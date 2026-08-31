from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


class ConfigurationError(RuntimeError):
    """Raised when deployment configuration is unsafe or incomplete."""


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _bool_env(name: str, default: bool) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    lowered = raw.lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    raise ConfigurationError(f"{name} must be a boolean value.")


def _csv_env(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    raw = _env(name)
    if raw is None:
        return default
    values = tuple(part.strip().rstrip("/") for part in raw.split(",") if part.strip())
    return values


def _positive_int_env(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return value


def _default_runtime_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    environment: str
    frontend_origins: tuple[str, ...]
    trusted_hosts: tuple[str, ...]
    secure_cookie: bool
    cookie_name: str
    runtime_root: Path
    auth_storage: Path
    data_storage: Path
    upload_max_bytes: int
    security_headers_enabled: bool
    hsts_max_age: int
    auth_login_ip_limit: int
    auth_login_email_limit: int
    auth_login_window_seconds: int
    auth_signup_ip_limit: int
    auth_signup_email_limit: int
    auth_signup_window_seconds: int
    auth_session_idle_seconds: int
    auth_session_max_seconds: int

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def load_settings() -> Settings:
    environment = (_env("V4_ENVIRONMENT", "development") or "development").lower()
    allowed_environments = {"development", "test", "staging", "production"}
    if environment not in allowed_environments:
        raise ConfigurationError(
            "V4_ENVIRONMENT must be one of: development, test, staging, production."
        )

    default_frontend_origins = ("http://localhost:3000",)
    frontend_origins = _csv_env("V4_FRONTEND_ORIGINS", default_frontend_origins)

    default_trusted_hosts = ("localhost", "127.0.0.1", "testserver")
    trusted_hosts = _csv_env("V4_TRUSTED_HOSTS", default_trusted_hosts)

    default_runtime_root = _default_runtime_root()
    runtime_raw = _env("V4_RUNTIME_ROOT")
    if environment == "production" and runtime_raw is None:
        raise ConfigurationError(
            "V4_RUNTIME_ROOT is required when V4_ENVIRONMENT=production."
        )
    runtime_root = Path(runtime_raw).expanduser().resolve() if runtime_raw else default_runtime_root

    secure_cookie_default = environment in {"production", "staging"}
    secure_cookie = _bool_env("V4_AUTH_SECURE_COOKIE", secure_cookie_default)
    if environment == "production" and not secure_cookie:
        raise ConfigurationError(
            "V4_AUTH_SECURE_COOKIE must be true in production."
        )

    cookie_name = _env("V4_AUTH_COOKIE_NAME", "v4_auth_session") or "v4_auth_session"
    if environment == "production" and not cookie_name.startswith("__Host-"):
        raise ConfigurationError(
            "Production auth cookie name must use the __Host- prefix."
        )

    auth_storage = Path(
        _env("V4_AUTH_STORAGE") or (runtime_root / "runtime_saas")
    ).expanduser().resolve()
    data_storage = Path(
        _env("V4_DATA_STORAGE") or (runtime_root / "runtime_data")
    ).expanduser().resolve()

    if environment == "production":
        if not frontend_origins:
            raise ConfigurationError("V4_FRONTEND_ORIGINS is required in production.")
        if not trusted_hosts:
            raise ConfigurationError("V4_TRUSTED_HOSTS is required in production.")
        for origin in frontend_origins:
            if not origin.startswith("https://"):
                raise ConfigurationError(
                    "All production V4_FRONTEND_ORIGINS must use HTTPS."
                )
        if any(host in {"localhost", "127.0.0.1", "0.0.0.0"} for host in trusted_hosts):
            raise ConfigurationError(
                "Production V4_TRUSTED_HOSTS cannot contain localhost loopback hosts."
            )

    upload_max_bytes = _positive_int_env("V4_UPLOAD_MAX_BYTES", 50 * 1024 * 1024)

    security_headers_enabled = _bool_env(
        "V4_SECURITY_HEADERS_ENABLED",
        environment in {"staging", "production"},
    )
    hsts_max_age = _positive_int_env("V4_HSTS_MAX_AGE", 31536000)

    auth_login_ip_limit = _positive_int_env("V4_AUTH_LOGIN_IP_LIMIT", 20)
    auth_login_email_limit = _positive_int_env("V4_AUTH_LOGIN_EMAIL_LIMIT", 8)
    auth_login_window_seconds = _positive_int_env("V4_AUTH_LOGIN_WINDOW_SECONDS", 900)
    auth_signup_ip_limit = _positive_int_env("V4_AUTH_SIGNUP_IP_LIMIT", 10)
    auth_signup_email_limit = _positive_int_env("V4_AUTH_SIGNUP_EMAIL_LIMIT", 3)
    auth_signup_window_seconds = _positive_int_env("V4_AUTH_SIGNUP_WINDOW_SECONDS", 3600)

    auth_session_idle_seconds = _positive_int_env(
        "V4_AUTH_SESSION_IDLE_SECONDS", 1800
    )
    auth_session_max_seconds = _positive_int_env(
        "V4_AUTH_SESSION_MAX_SECONDS", 604800
    )
    if auth_session_idle_seconds >= auth_session_max_seconds:
        raise ConfigurationError(
            "V4_AUTH_SESSION_IDLE_SECONDS must be less than "
            "V4_AUTH_SESSION_MAX_SECONDS."
        )

    if environment == "production" and not security_headers_enabled:
        raise ConfigurationError(
            "V4_SECURITY_HEADERS_ENABLED must be true in production."
        )

    return Settings(
        environment=environment,
        frontend_origins=frontend_origins,
        trusted_hosts=trusted_hosts,
        secure_cookie=secure_cookie,
        cookie_name=cookie_name,
        runtime_root=runtime_root,
        auth_storage=auth_storage,
        data_storage=data_storage,
        upload_max_bytes=upload_max_bytes,
        security_headers_enabled=security_headers_enabled,
        hsts_max_age=hsts_max_age,
        auth_login_ip_limit=auth_login_ip_limit,
        auth_login_email_limit=auth_login_email_limit,
        auth_login_window_seconds=auth_login_window_seconds,
        auth_signup_ip_limit=auth_signup_ip_limit,
        auth_signup_email_limit=auth_signup_email_limit,
        auth_signup_window_seconds=auth_signup_window_seconds,
        auth_session_idle_seconds=auth_session_idle_seconds,
        auth_session_max_seconds=auth_session_max_seconds,
    )


settings = load_settings()
