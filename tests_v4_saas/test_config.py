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
    assert settings.billing_provider == "disabled"
    assert settings.paddle_environment == "sandbox"


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
    monkeypatch.setenv("V4_SECURITY_HEADERS_ENABLED", "true")
    monkeypatch.setenv("V4_PERSISTENCE_MODE", "external")
    monkeypatch.setenv("V4_DATABASE_URL", "postgresql://user:password@example.com/app?sslmode=require")
    monkeypatch.setenv("V4_OBJECT_STORE_BUCKET", "app-data")
    monkeypatch.setenv("V4_OBJECT_STORE_REGION", "ap-south-1")
    monkeypatch.setenv("V4_OBJECT_STORE_ENDPOINT_URL", "https://objects.example.com")

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


def test_session_timeout_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("V4_AUTH_SESSION_IDLE_SECONDS", raising=False)
    monkeypatch.delenv("V4_AUTH_SESSION_MAX_SECONDS", raising=False)

    settings = load_settings()

    assert settings.auth_session_idle_seconds == 1800
    assert settings.auth_session_max_seconds == 604800


def test_session_idle_timeout_must_be_less_than_absolute_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("V4_AUTH_SESSION_IDLE_SECONDS", "604800")
    monkeypatch.setenv("V4_AUTH_SESSION_MAX_SECONDS", "604800")

    with pytest.raises(
        ConfigurationError,
        match="V4_AUTH_SESSION_IDLE_SECONDS must be less than",
    ):
        load_settings()


def test_persistence_mode_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("V4_PERSISTENCE_MODE", raising=False)
    settings = load_settings()
    assert settings.persistence_mode == "local"


def test_production_can_declare_external_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V4_ENVIRONMENT", "production")
    monkeypatch.setenv("V4_RUNTIME_ROOT", "/srv/ai-sales-analyst")
    monkeypatch.setenv("V4_FRONTEND_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("V4_TRUSTED_HOSTS", "api.example.com")
    monkeypatch.setenv("V4_AUTH_SECURE_COOKIE", "true")
    monkeypatch.setenv("V4_AUTH_COOKIE_NAME", "__Host-v4_auth_session")
    monkeypatch.setenv("V4_SECURITY_HEADERS_ENABLED", "true")
    monkeypatch.setenv("V4_PERSISTENCE_MODE", "external")
    monkeypatch.setenv("V4_SECURITY_HEADERS_ENABLED", "true")
    monkeypatch.setenv("V4_DATABASE_URL", "postgresql://user:password@example.com/app?sslmode=require")
    monkeypatch.setenv("V4_OBJECT_STORE_BUCKET", "app-data")
    monkeypatch.setenv("V4_OBJECT_STORE_REGION", "ap-south-1")
    monkeypatch.setenv("V4_OBJECT_STORE_ENDPOINT_URL", "https://objects.example.com")

    settings = load_settings()

    assert settings.is_production
    assert settings.persistence_mode == "external"


def test_external_persistence_requires_provider_configuration(monkeypatch):
    monkeypatch.setenv("V4_PERSISTENCE_MODE", "external")
    monkeypatch.delenv("V4_DATABASE_URL", raising=False)
    monkeypatch.delenv("V4_OBJECT_STORE_BUCKET", raising=False)
    monkeypatch.delenv("V4_OBJECT_STORE_REGION", raising=False)
    with pytest.raises(ConfigurationError, match="V4_DATABASE_URL"):
        load_settings()

def test_production_requires_external_persistence(monkeypatch):
    for key, value in {"V4_ENVIRONMENT":"production","V4_RUNTIME_ROOT":"/srv/ai-sales-analyst","V4_FRONTEND_ORIGINS":"https://app.example.com","V4_TRUSTED_HOSTS":"api.example.com","V4_AUTH_SECURE_COOKIE":"true","V4_AUTH_COOKIE_NAME":"__Host-v4_auth_session","V4_SECURITY_HEADERS_ENABLED":"true","V4_PERSISTENCE_MODE":"local"}.items(): monkeypatch.setenv(key,value)
    with pytest.raises(ConfigurationError, match="must be external"):
        load_settings()


def test_cache_max_bytes_cannot_be_less_than_upload_max_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('V4_UPLOAD_MAX_BYTES', '1000')
    monkeypatch.setenv('V4_CACHE_MAX_BYTES', '500')
    with pytest.raises(ConfigurationError, match='V4_CACHE_MAX_BYTES cannot be less than V4_UPLOAD_MAX_BYTES.'):
        load_settings()

def test_cache_max_bytes_equals_upload_max_bytes_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('V4_UPLOAD_MAX_BYTES', '1000')
    monkeypatch.setenv('V4_CACHE_MAX_BYTES', '1000')
    settings = load_settings()
    assert settings.cache_max_bytes == 1000
    assert settings.upload_max_bytes == 1000


def test_paddle_billing_requires_complete_provider_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "V4_BILLING_PROVIDER": "paddle",
        "V4_PADDLE_ENVIRONMENT": "sandbox",
        "V4_PADDLE_API_KEY": "pdl_sdbx_test",
        "V4_PADDLE_WEBHOOK_SECRET": "whsec_test",
        "V4_PADDLE_STARTER_PRICE_ID": "pri_starter",
        "V4_PADDLE_GROWTH_PRICE_ID": "pri_growth",
    }.items():
        monkeypatch.setenv(key, value)

    settings = load_settings()

    assert settings.billing_provider == "paddle"
    assert settings.paddle_environment == "sandbox"
    assert settings.paddle_starter_price_id == "pri_starter"
    assert settings.paddle_growth_price_id == "pri_growth"


def test_paddle_billing_rejects_live_key_in_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V4_BILLING_PROVIDER", "paddle")
    monkeypatch.setenv("V4_PADDLE_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("V4_PADDLE_API_KEY", "pdl_live_test")
    monkeypatch.setenv("V4_PADDLE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("V4_PADDLE_STARTER_PRICE_ID", "pri_starter")
    monkeypatch.setenv("V4_PADDLE_GROWTH_PRICE_ID", "pri_growth")

    with pytest.raises(ConfigurationError, match="Sandbox Paddle API keys"):
        load_settings()
