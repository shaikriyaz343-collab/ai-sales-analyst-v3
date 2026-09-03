import sys
import pytest
from unittest.mock import MagicMock, call

from backend.api.config import load_settings, ConfigurationError
from backend.api import runtime_persistence as runtime
from backend.api import persistence

def test_c4d2_configuration_defaults_and_validation(monkeypatch):
    monkeypatch.delenv("V4_DATABASE_POOL_MIN", raising=False)
    monkeypatch.delenv("V4_DATABASE_POOL_MAX", raising=False)
    monkeypatch.delenv("V4_DATABASE_TIMEOUT_CONNECT", raising=False)
    monkeypatch.delenv("V4_DATABASE_TIMEOUT_STATEMENT", raising=False)
    monkeypatch.delenv("V4_DATABASE_TIMEOUT_POOL", raising=False)
    monkeypatch.delenv("V4_OBJECT_STORE_TIMEOUT_CONNECT", raising=False)
    monkeypatch.delenv("V4_OBJECT_STORE_TIMEOUT_READ", raising=False)

    settings = load_settings()
    assert settings.database_pool_min == 4
    assert settings.database_pool_max == 20
    assert settings.database_timeout_connect == 5
    assert settings.database_timeout_statement == 30000
    assert settings.database_timeout_pool == 10
    assert settings.object_store_timeout_connect == 5
    assert settings.object_store_timeout_read == 15

    # Overrides
    monkeypatch.setenv("V4_DATABASE_POOL_MIN", "10")
    monkeypatch.setenv("V4_DATABASE_POOL_MAX", "50")
    settings = load_settings()
    assert settings.database_pool_min == 10
    assert settings.database_pool_max == 50

    # Max < Min
    monkeypatch.setenv("V4_DATABASE_POOL_MAX", "2")
    with pytest.raises(ConfigurationError, match="V4_DATABASE_POOL_MAX cannot be less than V4_DATABASE_POOL_MIN"):
        load_settings()

    # Invalid negative
    monkeypatch.setenv("V4_DATABASE_POOL_MIN", "-1")
    monkeypatch.setenv("V4_DATABASE_POOL_MAX", "20")
    with pytest.raises(ConfigurationError):
        load_settings()

def test_c4d2_postgres_constructor(monkeypatch):
    mock_psycopg_pool = MagicMock()
    monkeypatch.setitem(sys.modules, "psycopg_pool", mock_psycopg_pool)

    runtime.settings = MagicMock()
    runtime.settings.database_pool_min = 2
    runtime.settings.database_pool_max = 8
    runtime.settings.database_timeout_pool = 15
    runtime.settings.database_timeout_connect = 7
    runtime.settings.database_timeout_statement = 45000

    pool = runtime.PsycopgConnectionPool("postgresql://fake")

    mock_psycopg_pool.ConnectionPool.assert_called_once_with(
        "postgresql://fake",
        min_size=2,
        max_size=8,
        timeout=15,
        max_lifetime=3600,
        kwargs={
            "connect_timeout": 7,
            "options": "-c statement_timeout=45000"
        },
        open=False
    )

def test_c4d2_boto3_constructor(monkeypatch):
    mock_boto3 = MagicMock()
    monkeypatch.setitem(sys.modules, "boto3", mock_boto3)

    persistence.settings = MagicMock()
    persistence.settings.object_store_timeout_connect = 4
    persistence.settings.object_store_timeout_read = 12

    store = persistence.S3ObjectStore(
        bucket="b", region="r", prefix="p", temp_root=None,
        endpoint_url=None, access_key=None, secret_key=None
    )

    # Assert botocore.config.Config was passed correctly
    kwargs = mock_boto3.client.call_args.kwargs
    config_obj = kwargs.get("config")

    assert config_obj is not None
    assert config_obj.connect_timeout == 4
    assert config_obj.read_timeout == 12
    assert config_obj.retries == {'max_attempts': 3}

def test_c4d2_transaction_cleanup_on_statement_timeout(monkeypatch):
    # This tests the semantic contract that when an exception (like statement timeout)
    # bubbles up, the pool context manager handles returning/closing the connection properly,
    # ensuring the next borrower gets a clean one.

    mock_psycopg_pool = MagicMock()
    mock_pool_instance = MagicMock()
    mock_psycopg_pool.ConnectionPool.return_value = mock_pool_instance
    monkeypatch.setitem(sys.modules, "psycopg_pool", mock_psycopg_pool)

    pool = runtime.PsycopgConnectionPool("postgresql://fake")

    mock_conn = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_conn
    mock_pool_instance.connection.return_value = mock_ctx

    class StatementTimeoutError(Exception):
        pass

    with pytest.raises(StatementTimeoutError):
        with pool.connection() as conn:
            raise StatementTimeoutError("canceling statement due to statement timeout")

    # The pool context manager should have exited cleanly (passing the exception to __exit__)
    mock_ctx.__exit__.assert_called_once()
    exc_type, exc_val, exc_tb = mock_ctx.__exit__.call_args[0]
    assert exc_type is StatementTimeoutError
    assert "canceling statement" in str(exc_val)
