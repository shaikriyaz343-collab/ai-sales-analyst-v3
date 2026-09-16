from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.api.config import ConfigurationError, load_settings
import backend.api.main as main


def _production_env(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> None:
    values = {
        "V4_ENVIRONMENT": "production",
        "V4_RUNTIME_ROOT": "/srv/ai-sales-analyst",
        "V4_FRONTEND_ORIGINS": "https://app.example.com",
        "V4_TRUSTED_HOSTS": "api.example.com",
        "V4_AUTH_SECURE_COOKIE": "true",
        "V4_AUTH_COOKIE_NAME": "__Host-v4_auth_session",
        "V4_SECURITY_HEADERS_ENABLED": "true",
        "V4_PERSISTENCE_MODE": "external",
        "V4_DATABASE_URL": "postgresql://user:password@example.com/app?sslmode=require",
        "V4_OBJECT_STORE_BUCKET": "app-data",
        "V4_OBJECT_STORE_REGION": "ap-south-1",
        "V4_OBJECT_STORE_ENDPOINT_URL": "https://objects.example.com",
        **overrides,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_samesite_none_requires_secure_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V4_ENVIRONMENT", "staging")
    monkeypatch.setenv("V4_AUTH_SECURE_COOKIE", "false")
    monkeypatch.setenv("V4_AUTH_COOKIE_SAMESITE", "none")

    with pytest.raises(ConfigurationError, match="V4_AUTH_COOKIE_SAMESITE=none requires V4_AUTH_SECURE_COOKIE=true"):
        load_settings()


def test_security_headers_are_present_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "settings", replace(main.settings, security_headers_enabled=True, environment="staging"))

    with TestClient(main.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["permissions-policy"]


def test_cors_allows_declared_origin_and_credentials() -> None:
    with TestClient(main.app) as client:
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_does_not_echo_undeclared_origin() -> None:
    with TestClient(main.app) as client:
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
