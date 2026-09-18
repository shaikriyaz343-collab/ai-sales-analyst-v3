from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse


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

def _samesite_env(name: str, default: str) -> str:
    raw = (_env(name, default) or default).lower()
    if raw not in {"lax", "strict", "none"}:
        raise ConfigurationError(f"{name} must be one of: lax, strict, none.")
    return raw

def _default_runtime_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    environment: str
    frontend_origins: tuple[str, ...]
    trusted_hosts: tuple[str, ...]
    secure_cookie: bool
    auth_cookie_samesite: str
    cookie_name: str
    runtime_root: Path
    auth_storage: Path
    data_storage: Path
    upload_max_bytes: int
    cache_max_bytes: int
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
    database_pool_min: int
    database_pool_max: int
    database_timeout_connect: int
    database_timeout_statement: int
    database_timeout_pool: int
    analytics_concurrency: int
    object_store_timeout_connect: int
    object_store_timeout_read: int
    persistence_mode: str
    database_url: str | None = field(repr=False)
    object_store_bucket: str | None
    object_store_region: str | None
    object_store_endpoint_url: str | None
    object_store_access_key: str | None = field(repr=False)
    object_store_secret_key: str | None = field(repr=False)
    object_store_prefix: str
    object_store_temp_root: Path
    billing_provider: str
    paddle_environment: str
    paddle_api_key: str | None = field(repr=False)
    paddle_webhook_secret: str | None = field(repr=False)
    paddle_starter_price_id: str | None
    paddle_growth_price_id: str | None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"



def _validate_production_external_configuration(
    *,
    database_url: str,
    object_store_bucket: str,
    object_store_region: str,
    object_store_endpoint_url: str | None,
    object_store_access_key: str | None,
    object_store_secret_key: str | None,
    object_store_prefix: str,
) -> None:
    """Validate production external persistence without exposing secret values."""
    parsed_database = urlparse(database_url)
    if parsed_database.scheme not in {"postgresql", "postgres"}:
        raise ConfigurationError(
            "V4_DATABASE_URL must use a PostgreSQL URL scheme in production."
        )
    if not parsed_database.hostname:
        raise ConfigurationError(
            "V4_DATABASE_URL must include a database host in production."
        )

    query = parse_qs(parsed_database.query)
    ssl_modes = {mode.lower() for mode in query.get("sslmode", [])}
    if not ssl_modes.intersection({"require", "verify-ca", "verify-full"}):
        raise ConfigurationError(
            "Production V4_DATABASE_URL must explicitly enable TLS via sslmode=require, verify-ca, or verify-full."
        )

    if object_store_endpoint_url:
        parsed_endpoint = urlparse(object_store_endpoint_url)
        if parsed_endpoint.scheme != "https":
            raise ConfigurationError(
                "V4_OBJECT_STORE_ENDPOINT_URL must use HTTPS in production."
            )

    if bool(object_store_access_key) != bool(object_store_secret_key):
        raise ConfigurationError(
            "V4_OBJECT_STORE_ACCESS_KEY and V4_OBJECT_STORE_SECRET_KEY must be provided together."
        )

    normalized_prefix = object_store_prefix.strip("/")
    if not normalized_prefix:
        raise ConfigurationError(
            "V4_OBJECT_STORE_PREFIX must not be empty in production."
        )
    if any(part == ".." for part in normalized_prefix.replace("\\", "/").split("/")):
        raise ConfigurationError(
            "V4_OBJECT_STORE_PREFIX cannot contain parent-directory segments."
        )


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
    auth_cookie_samesite = _samesite_env("V4_AUTH_COOKIE_SAMESITE", "lax")
    if auth_cookie_samesite == "none" and not secure_cookie:
        raise ConfigurationError(
            "V4_AUTH_COOKIE_SAMESITE=none requires V4_AUTH_SECURE_COOKIE=true."
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
    cache_max_bytes = _positive_int_env("V4_CACHE_MAX_BYTES", 5 * 1024 * 1024 * 1024)

    if cache_max_bytes < upload_max_bytes:
        raise ConfigurationError(
            "V4_CACHE_MAX_BYTES cannot be less than V4_UPLOAD_MAX_BYTES."
        )

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

    database_pool_min = _positive_int_env("V4_DATABASE_POOL_MIN", 4)
    database_pool_max = _positive_int_env("V4_DATABASE_POOL_MAX", 20)
    if database_pool_max < database_pool_min:
        raise ConfigurationError("V4_DATABASE_POOL_MAX cannot be less than V4_DATABASE_POOL_MIN.")

    database_timeout_connect = _positive_int_env("V4_DATABASE_TIMEOUT_CONNECT", 5)
    database_timeout_statement = _positive_int_env("V4_DATABASE_TIMEOUT_STATEMENT", 30000)
    database_timeout_pool = _positive_int_env("V4_DATABASE_TIMEOUT_POOL", 10)

    object_store_timeout_connect = _positive_int_env("V4_OBJECT_STORE_TIMEOUT_CONNECT", 5)
    object_store_timeout_read = _positive_int_env("V4_OBJECT_STORE_TIMEOUT_READ", 15)

    persistence_mode = (_env("V4_PERSISTENCE_MODE", "local") or "local").lower()
    if persistence_mode not in {"local", "external"}:
        raise ConfigurationError("V4_PERSISTENCE_MODE must be local or external.")
    database_url = _env("V4_DATABASE_URL")
    object_store_bucket = _env("V4_OBJECT_STORE_BUCKET")
    object_store_region = _env("V4_OBJECT_STORE_REGION")
    object_store_endpoint_url = _env("V4_OBJECT_STORE_ENDPOINT_URL")
    object_store_access_key = _env("V4_OBJECT_STORE_ACCESS_KEY")
    object_store_secret_key = _env("V4_OBJECT_STORE_SECRET_KEY")
    object_store_prefix = _env("V4_OBJECT_STORE_PREFIX", "v4") or "v4"
    object_store_temp_root = Path(_env("V4_OBJECT_STORE_TEMP_ROOT") or (runtime_root / "runtime_object_cache")).expanduser().resolve()

    billing_provider = (_env("V4_BILLING_PROVIDER", "disabled") or "disabled").lower()
    if billing_provider not in {"disabled", "paddle"}:
        raise ConfigurationError("V4_BILLING_PROVIDER must be disabled or paddle.")
    paddle_environment = (_env("V4_PADDLE_ENVIRONMENT", "sandbox") or "sandbox").lower()
    if paddle_environment not in {"sandbox", "live"}:
        raise ConfigurationError("V4_PADDLE_ENVIRONMENT must be sandbox or live.")
    paddle_api_key = _env("V4_PADDLE_API_KEY")
    paddle_webhook_secret = _env("V4_PADDLE_WEBHOOK_SECRET")
    paddle_starter_price_id = _env("V4_PADDLE_STARTER_PRICE_ID")
    paddle_growth_price_id = _env("V4_PADDLE_GROWTH_PRICE_ID")
    if billing_provider == "paddle":
        required = {
            "V4_PADDLE_API_KEY": paddle_api_key,
            "V4_PADDLE_WEBHOOK_SECRET": paddle_webhook_secret,
            "V4_PADDLE_STARTER_PRICE_ID": paddle_starter_price_id,
            "V4_PADDLE_GROWTH_PRICE_ID": paddle_growth_price_id,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ConfigurationError(
                "Paddle billing is enabled but required configuration is missing: " + ", ".join(missing)
            )
        if paddle_environment == "sandbox" and not paddle_api_key.startswith("pdl_sdbx_"):
            raise ConfigurationError("Sandbox Paddle API keys must use the sandbox key prefix.")
        if paddle_environment == "live" and not paddle_api_key.startswith("pdl_live_"):
            raise ConfigurationError("Live Paddle API keys must use the live key prefix.")
    if persistence_mode == "external":
        if not database_url: raise ConfigurationError("V4_DATABASE_URL is required when V4_PERSISTENCE_MODE=external.")
        if not object_store_bucket: raise ConfigurationError("V4_OBJECT_STORE_BUCKET is required when V4_PERSISTENCE_MODE=external.")
        if not object_store_region: raise ConfigurationError("V4_OBJECT_STORE_REGION is required when V4_PERSISTENCE_MODE=external.")
    if environment == "production" and persistence_mode != "external": raise ConfigurationError("V4_PERSISTENCE_MODE must be external in production.")
    if environment == "production" and not security_headers_enabled:
        raise ConfigurationError(
            "V4_SECURITY_HEADERS_ENABLED must be true in production."
        )

    if environment == "production":
        _validate_production_external_configuration(
            database_url=database_url,
            object_store_bucket=object_store_bucket,
            object_store_region=object_store_region,
            object_store_endpoint_url=object_store_endpoint_url,
            object_store_access_key=object_store_access_key,
            object_store_secret_key=object_store_secret_key,
            object_store_prefix=object_store_prefix,
        )

    return Settings(
        environment=environment,
        frontend_origins=frontend_origins,
        trusted_hosts=trusted_hosts,
        secure_cookie=secure_cookie,
        auth_cookie_samesite=auth_cookie_samesite,
        cookie_name=cookie_name,
        runtime_root=runtime_root,
        auth_storage=auth_storage,
        data_storage=data_storage,
        upload_max_bytes=upload_max_bytes,
        cache_max_bytes=cache_max_bytes,
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
        database_pool_min=database_pool_min,
        database_pool_max=database_pool_max,
        database_timeout_connect=database_timeout_connect,
        database_timeout_statement=database_timeout_statement,
        database_timeout_pool=database_timeout_pool,
        analytics_concurrency=_positive_int_env("V4_ANALYTICS_CONCURRENCY", 4),
        object_store_timeout_connect=object_store_timeout_connect,
        object_store_timeout_read=object_store_timeout_read,
        persistence_mode=persistence_mode,
        database_url=database_url,
        object_store_bucket=object_store_bucket,
        object_store_region=object_store_region,
        object_store_endpoint_url=object_store_endpoint_url,
        object_store_access_key=object_store_access_key,
        object_store_secret_key=object_store_secret_key,
        object_store_prefix=object_store_prefix,
        object_store_temp_root=object_store_temp_root,
        billing_provider=billing_provider,
        paddle_environment=paddle_environment,
        paddle_api_key=paddle_api_key,
        paddle_webhook_secret=paddle_webhook_secret,
        paddle_starter_price_id=paddle_starter_price_id,
        paddle_growth_price_id=paddle_growth_price_id,
    )


settings = load_settings()
