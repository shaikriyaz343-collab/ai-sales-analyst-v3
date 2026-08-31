from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import backend.api.services.auth as auth


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "AUTH_STORAGE", tmp_path / "auth")
    monkeypatch.setattr(auth, "AUTH_DB", tmp_path / "auth" / "auth.db")
    auth.init_db()
    from backend.api.main import app
    return TestClient(app)


def test_auth_signup_me_and_logout(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    response = client.post("/api/v1/auth/signup", json={"email": "owner@example.com", "password": "StrongPassword1!", "name": "Riyaz", "organization_name": "Acme"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "owner"
    assert response.cookies.get(auth.SESSION_COOKIE)

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["organization_name"] == "Acme"

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_protected_data_route_requires_auth(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    response = client.get("/api/v1/datasets/does-not-exist")
    assert response.status_code == 401


def test_workspace_create_requires_owner(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    response = client.post("/api/v1/workspaces", json={"name": "Finance"})
    assert response.status_code == 401


def test_tenant_cannot_read_another_org_dataset(tmp_path, monkeypatch):
    client_a = _client(tmp_path, monkeypatch)
    signup_a = client_a.post("/api/v1/auth/signup", json={"email": "a@example.com", "password": "StrongPassword1!", "name": "User A", "organization_name": "Org A"})
    assert signup_a.status_code == 200
    from pathlib import Path
    sample = Path(__file__).resolve().parents[1] / "samples" / "retail.csv"
    with sample.open("rb") as fh:
        uploaded = client_a.post("/api/v1/onboarding/profile", files={"file": ("retail.csv", fh, "text/csv")})
    assert uploaded.status_code == 200
    dataset_id = uploaded.json()["dataset"]["dataset_id"]

    client_b = TestClient(__import__("backend.api.main", fromlist=["app"]).app)
    signup_b = client_b.post("/api/v1/auth/signup", json={"email": "b@example.com", "password": "StrongPassword1!", "name": "User B", "organization_name": "Org B"})
    assert signup_b.status_code == 200
    assert client_b.get(f"/api/v1/datasets/{dataset_id}").status_code == 404
