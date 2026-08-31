from __future__ import annotations

from fastapi.testclient import TestClient

import backend.api.main as main
import backend.api.services.auth as auth


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "AUTH_STORAGE", tmp_path / "auth")
    monkeypatch.setattr(auth, "AUTH_DB", tmp_path / "auth" / "auth.db")
    auth.init_db()
    return TestClient(main.app)


def test_signup_duplicate_email_has_generic_public_response(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    payload = {
        "email": "owner@example.com",
        "password": "StrongPassword1!",
        "name": "Riyaz",
        "organization_name": "Acme",
    }
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 200

    duplicate = client.post("/api/v1/auth/signup", json=payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Unable to create this account."
    assert "already exists" not in duplicate.text
    assert "owner@example.com" not in duplicate.text


def test_login_rate_limit_applies_to_ip_and_email(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "LOGIN_RATE_LIMIT_IP", 2)
    monkeypatch.setattr(main, "LOGIN_RATE_LIMIT_EMAIL", 100)
    monkeypatch.setattr(main, "LOGIN_RATE_LIMIT_WINDOW", 3600)

    for _ in range(2):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "StrongPassword1!"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "StrongPassword1!"},
    )
    assert limited.status_code == 429


def test_login_rate_limit_applies_to_email_key(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "LOGIN_RATE_LIMIT_IP", 100)
    monkeypatch.setattr(main, "LOGIN_RATE_LIMIT_EMAIL", 2)
    monkeypatch.setattr(main, "LOGIN_RATE_LIMIT_WINDOW", 3600)

    for _ in range(2):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "StrongPassword1!"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "StrongPassword1!"},
    )
    assert limited.status_code == 429


def test_signup_rate_limit_and_security_event_do_not_store_raw_secret(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "SIGNUP_RATE_LIMIT_IP", 1)
    monkeypatch.setattr(main, "SIGNUP_RATE_LIMIT_EMAIL", 100)
    monkeypatch.setattr(main, "SIGNUP_RATE_LIMIT_WINDOW", 3600)

    payload = {
        "email": "limited@example.com",
        "password": "SuperSecretPassword123!",
        "name": "Limited User",
        "organization_name": "Acme",
    }
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 200

    limited = client.post(
        "/api/v1/auth/signup",
        json={**payload, "email": "second@example.com"},
    )
    assert limited.status_code == 429

    events = auth.list_security_events()
    assert any(event["event_type"] == "signup_rate_limited" for event in events)
    raw = repr(events)
    assert "SuperSecretPassword123!" not in raw
    assert "limited@example.com" not in raw


def test_auth_security_events_record_success_and_failure_without_raw_email(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    payload = {
        "email": "events@example.com",
        "password": "StrongPassword1!",
        "name": "Events User",
        "organization_name": "Acme",
    }
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 200
    client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "WrongPassword1!"},
    )

    events = auth.list_security_events()
    types = [event["event_type"] for event in events]
    assert "signup_success" in types
    assert "login_failed" in types
    raw = repr(events)
    assert payload["email"] not in raw
    assert "WrongPassword1!" not in raw
