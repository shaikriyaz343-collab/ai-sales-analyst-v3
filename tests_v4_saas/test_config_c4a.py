from __future__ import annotations

import pytest

from backend.api.config import ConfigurationError, load_settings


MANAGED = (
    "V4_ENVIRONMENT",
    "V4_RUNTIME_ROOT",
    "V4_AUTH_SECURE_COOKIE",
    "V4_AUTH_COOKIE_NAME",
    "V4_FRONTEND_ORIGINS",
    "V4_TRUSTED_HOSTS",
    "V4_SECURITY_HEADERS_ENABLED",
    "V4_PERSISTENCE_MODE",
    "V4_DATABASE_URL",
    "V4_OBJECT_STORE_BUCKET",
    "V4_OBJECT_STORE_REGION",
    "V4_OBJECT_STORE_ENDPOINT_URL",
    "V4_OBJECT_STORE_ACCESS_KEY",
    "V4_OBJECT_STORE_SECRET_KEY",
    "V4_OBJECT_STORE_PREFIX",
)


def clear(monkeypatch):
    for name in MANAGED:
        monkeypatch.delenv(name, raising=False)


def set_valid_production(monkeypatch):
    monkeypatch.setenv("V4_ENVIRONMENT", "production")
    monkeypatch.setenv("V4_RUNTIME_ROOT", r"C:\v4\runtime")
    monkeypatch.setenv("V4_FRONTEND_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("V4_TRUSTED_HOSTS", "api.example.com")
    monkeypatch.setenv("V4_AUTH_SECURE_COOKIE", "true")
    monkeypatch.setenv("V4_AUTH_COOKIE_NAME", "__Host-v4_auth_session")
    monkeypatch.setenv("V4_SECURITY_HEADERS_ENABLED", "true")
    monkeypatch.setenv("V4_PERSISTENCE_MODE", "external")
    monkeypatch.setenv(
        "V4_DATABASE_URL",
        "postgresql://app@example.com:5432/v4?sslmode=require",
    )
    monkeypatch.setenv("V4_OBJECT_STORE_BUCKET", "v4-production")
    monkeypatch.setenv("V4_OBJECT_STORE_REGION", "ap-south-1")
    monkeypatch.setenv("V4_OBJECT_STORE_PREFIX", "v4")
    monkeypatch.delenv("V4_OBJECT_STORE_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("V4_OBJECT_STORE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("V4_OBJECT_STORE_SECRET_KEY", raising=False)


def test_valid_production_external_configuration_is_accepted(monkeypatch):
    clear(monkeypatch)
    set_valid_production(monkeypatch)
    settings = load_settings()
    assert settings.is_production
    assert settings.persistence_mode == "external"


def test_production_requires_database_tls(monkeypatch):
    clear(monkeypatch)
    set_valid_production(monkeypatch)
    monkeypatch.setenv("V4_DATABASE_URL", "postgresql://app@example.com:5432/v4")
    with pytest.raises(ConfigurationError, match="TLS via sslmode"):
        load_settings()


def test_production_custom_object_store_endpoint_requires_https(monkeypatch):
    clear(monkeypatch)
    set_valid_production(monkeypatch)
    monkeypatch.setenv("V4_OBJECT_STORE_ENDPOINT_URL", "http://objects.example.com")
    with pytest.raises(ConfigurationError, match="must use HTTPS"):
        load_settings()


def test_object_store_credentials_must_be_paired(monkeypatch):
    clear(monkeypatch)
    set_valid_production(monkeypatch)
    monkeypatch.setenv("V4_OBJECT_STORE_ACCESS_KEY", "access")
    monkeypatch.delenv("V4_OBJECT_STORE_SECRET_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="provided together"):
        load_settings()


def test_secret_bearing_settings_are_excluded_from_repr(monkeypatch):
    clear(monkeypatch)
    set_valid_production(monkeypatch)
    monkeypatch.setenv(
        "V4_DATABASE_URL",
        "postgresql://very_secret_user:very_secret_password@example.com:5432/v4?sslmode=require",
    )
    monkeypatch.setenv("V4_OBJECT_STORE_ACCESS_KEY", "very-secret-access")
    monkeypatch.setenv("V4_OBJECT_STORE_SECRET_KEY", "very-secret-secret")
    rendered = repr(load_settings())
    assert "very_secret_password" not in rendered
    assert "very-secret-access" not in rendered
    assert "very-secret-secret" not in rendered


def test_local_development_defaults_remain_local(monkeypatch):
    clear(monkeypatch)
    settings = load_settings()
    assert settings.environment == "development"
    assert settings.persistence_mode == "local"
    assert settings.secure_cookie is False
