from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

import backend.api.main as main
from backend.api.config import Settings


def _settings_for_headers(enabled: bool) -> Settings:
    return replace(
        main.settings,
        security_headers_enabled=enabled,
    )


def test_development_response_security_headers_are_present_when_enabled(monkeypatch):
    monkeypatch.setattr(main, "settings", _settings_for_headers(True))
    client = TestClient(main.app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"


def test_development_response_security_headers_can_be_disabled(monkeypatch):
    monkeypatch.setattr(main, "settings", _settings_for_headers(False))
    client = TestClient(main.app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert "X-Content-Type-Options" not in response.headers
    assert "X-Frame-Options" not in response.headers
    assert "Strict-Transport-Security" not in response.headers
