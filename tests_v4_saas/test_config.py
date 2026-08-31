from __future__ import annotations

import pytest

from backend.api.config import ConfigurationError, load_settings


def test_development_defaults_preserve_local_runtime_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "V4_ENVIRONMENT",
        "V4_FRONTEND_ORIGINS",
        "V4_TRUSTED_HOSTS",
        "V4_AUTH_SECURE_COOKIE",
        "V4_AUTH_COOKIE_NAME",
        "V4_RUNTIME_ROOT",
        "V4_AUTH_STORAGE",
        "V4_DATA_STORAGE",
        "V4_UPLOAD_MAX_BYTES",
        "V4_AUTH_LOGIN_IP_LIMIT", "V4_AUTH_LOGIN_EMAIL_LIMIT", "V4_AUTH_LOGIN_WINDOW_SECONDS",
        "V4_AUTH_SIGNUP_IP_LIMIT", "V4_AUTH_SIGNUP_EMAIL_LIMIT", "V4_AUTH_SIGNUP_WINDOW_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = load_settings()
    assert settings.environment == "development"
    assert settings.frontend_origins == ("http://localhost:3000",)
    assert settings.trusted_hosts == ("localhost", "127.0.0.1", "testserver")
    assert settings.secure_cookie is False
    assert settings.cookie_name == "v4_auth_session"
    assert settings.upload_max_bytes == 50 * 1024 * 1024
    assert settings.auth_login_ip_limit == 20
    assert settings.auth_login_email_limit == 8
    assert settings.auth_login_window_seconds == 900
    assert settings.auth_signup_ip_limit == 10
    assert settings.auth_signup_email_limit == 3
    assert settings.auth_signup_window_seconds == 3600


def test_production_requires_explicit_runtime_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V4_ENVIRONMENT", "production")
    monkeypatch.delenv("V4_RUNTIME_ROOT", raising=False)

    with pytest.raises(ConfigurationError, match="V4_RUNTIME_ROOT is required"):
        load_settings()


def test_production_requires_secure_host_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V4_ENVIRONMENT", "production")
    monkeypatch.setenv("V4_RUNTIME_ROOT", "/srv/ai-sales-analyst")
    monkeypatch.setenv("V4_FRONTEND_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("V4_TRUSTED_HOSTS", "api.example.com")
    monkeypatch.setenv("V4_AUTH_SECURE_COOKIE", "true")
    monkeypatch.setenv("V4_AUTH_COOKIE_NAME", "__Host-v4_auth_session")

    settings = load_settings()
    assert settings.is_production
    assert settings.secure_cookie is True
    assert settings.cookie_name == "__Host-v4_auth_session"
    assert settings.frontend_origins == ("https://app.example.com",)
    assert settings.trusted_hosts == ("api.example.com",)


def test_production_rejects_http_frontend_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V4_ENVIRONMENT", "production")
    monkeypatch.setenv("V4_RUNTIME_ROOT", "/srv/ai-sales-analyst")
    monkeypatch.setenv("V4_FRONTEND_ORIGINS", "http://app.example.com")
    monkeypatch.setenv("V4_TRUSTED_HOSTS", "api.example.com")
    monkeypatch.setenv("V4_AUTH_SECURE_COOKIE", "true")
    monkeypatch.setenv("V4_AUTH_COOKIE_NAME", "__Host-v4_auth_session")

    with pytest.raises(ConfigurationError, match="must use HTTPS"):
        load_settings()


def test_production_rejects_loopback_trusted_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V4_ENVIRONMENT", "production")
    monkeypatch.setenv("V4_RUNTIME_ROOT", "/srv/ai-sales-analyst")
    monkeypatch.setenv("V4_FRONTEND_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("V4_TRUSTED_HOSTS", "localhost")
    monkeypatch.setenv("V4_AUTH_SECURE_COOKIE", "true")
    monkeypatch.setenv("V4_AUTH_COOKIE_NAME", "__Host-v4_auth_session")

    with pytest.raises(ConfigurationError, match="cannot contain localhost"):
        load_settings()


def test_production_rejects_non_host_cookie_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V4_ENVIRONMENT", "production")
    monkeypatch.setenv("V4_RUNTIME_ROOT", "/srv/ai-sales-analyst")
    monkeypatch.setenv("V4_FRONTEND_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("V4_TRUSTED_HOSTS", "api.example.com")
    monkeypatch.setenv("V4_AUTH_SECURE_COOKIE", "true")
    monkeypatch.setenv("V4_AUTH_COOKIE_NAME", "v4_auth_session")

    with pytest.raises(ConfigurationError, match="__Host-"):
        load_settings()
