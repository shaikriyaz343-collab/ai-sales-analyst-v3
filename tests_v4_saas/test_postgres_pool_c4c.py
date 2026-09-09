import pytest
from unittest.mock import MagicMock, patch
import sys
from types import SimpleNamespace
from pathlib import Path

import backend.api.runtime_persistence as runtime
from backend.api.config import settings
from backend.api.services.auth import _external_auth_store, reset_external_auth, set_external_auth
from backend.api.services.auth_postgres import PostgresAuthStore
from backend.api.persistence import PostgresJsonDocumentStore
from backend.api.main import lifespan
from fastapi import FastAPI
import asyncio


@pytest.fixture(autouse=True)
def clean_state():
    runtime.reset_runtime_persistence()
    reset_external_auth()
    yield
    runtime.reset_runtime_persistence()
    reset_external_auth()


def _settings(tmp_path):
    return SimpleNamespace(
        persistence_mode="external",
        runtime_root=tmp_path,
        database_url="postgresql://user:pass@example.com/app",
        object_store_bucket="bucket",
        object_store_region="ap-south-1",
        object_store_endpoint_url=None,
        object_store_access_key=None,
        object_store_secret_key=None,
        object_store_prefix="v4",
        object_store_temp_root=tmp_path / "cache",
        analytics_concurrency=4,
    )


def _context():
    return SimpleNamespace(
        mode="external",
        objects=MagicMock(),
        datasets=MagicMock(),
        sessions=MagicMock(),
        monitoring=MagicMock(),
        saved_intelligence=MagicMock(),
    )


def run_async(coro):
    return asyncio.run(coro)

def test_external_lifecycle_success(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "settings", _settings(tmp_path))
    monkeypatch.setattr("backend.api.main.settings", _settings(tmp_path))
    monkeypatch.setattr("backend.api.services.auth.settings", _settings(tmp_path))

    mock_pool_class = MagicMock()
    mock_pool_instance = MagicMock()
    mock_pool_class.return_value = mock_pool_instance
    monkeypatch.setattr(runtime, "PsycopgConnectionPool", mock_pool_class)

    context = _context()
    monkeypatch.setattr(runtime, "build_persistence", MagicMock(return_value=context))

    mock_auth_store = MagicMock()
    monkeypatch.setattr("backend.api.services.auth_postgres.PostgresAuthStore", mock_auth_store)

    app = FastAPI()

    async def _test():
        async with lifespan(app):
            # 1. Pool created exactly once
            mock_pool_class.assert_called_once_with("postgresql://user:pass@example.com/app")
            # 2. Explicitly opened
            mock_pool_instance.open.assert_called_once()
            # 3. Runtime persistence initialized
            assert runtime.get_runtime_persistence() is context
            # 4. Auth store initialized with SAME provider
            mock_auth_store.assert_called_once_with("postgresql://user:pass@example.com/app", provider=mock_pool_instance)
            # Auth store cached
            assert _external_auth_store() is mock_auth_store.return_value

    run_async(_test())

    # Shutdown
    # 5. Auth reset
    with pytest.raises(RuntimeError, match="External auth store accessed before lifecycle startup"):
        _external_auth_store()

    # 6. Runtime reset
    with pytest.raises(RuntimeError, match="External runtime persistence was accessed before lifecycle startup"):
        runtime.get_runtime_persistence()

    # 7. Provider closed exactly once
    mock_pool_instance.close.assert_called_once()


def test_external_lifecycle_runtime_persistence_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "settings", _settings(tmp_path))
    monkeypatch.setattr("backend.api.main.settings", _settings(tmp_path))
    monkeypatch.setattr("backend.api.services.auth.settings", _settings(tmp_path))

    mock_pool_class = MagicMock()
    mock_pool_instance = MagicMock()
    mock_pool_class.return_value = mock_pool_instance
    monkeypatch.setattr(runtime, "PsycopgConnectionPool", mock_pool_class)

    monkeypatch.setattr(runtime, "build_persistence", MagicMock(side_effect=Exception("Failed to build")))

    app = FastAPI()

    async def _test():
        async with lifespan(app):
            pass

    with pytest.raises(Exception, match="Failed to build"):
        run_async(_test())

    # Ensure closed
    mock_pool_instance.close.assert_called_once()


def test_external_lifecycle_auth_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "settings", _settings(tmp_path))
    monkeypatch.setattr("backend.api.main.settings", _settings(tmp_path))
    monkeypatch.setattr("backend.api.services.auth.settings", _settings(tmp_path))

    mock_pool_class = MagicMock()
    mock_pool_instance = MagicMock()
    mock_pool_class.return_value = mock_pool_instance
    monkeypatch.setattr(runtime, "PsycopgConnectionPool", mock_pool_class)

    context = _context()
    monkeypatch.setattr(runtime, "build_persistence", MagicMock(return_value=context))

    mock_auth_store = MagicMock(side_effect=Exception("Auth init failed"))
    monkeypatch.setattr("backend.api.services.auth_postgres.PostgresAuthStore", mock_auth_store)

    app = FastAPI()

    async def _test():
        async with lifespan(app):
            pass

    with pytest.raises(Exception, match="Auth init failed"):
        run_async(_test())

    # Ensure closed via finally block
    mock_pool_instance.close.assert_called_once()


def test_psycopg_pool_readiness_failure_double_close(monkeypatch):
    # PsycopgConnectionPool readiness fail does not double close
    mock_psycopg_pool = MagicMock()
    mock_pool = MagicMock()
    mock_psycopg_pool.ConnectionPool.return_value = mock_pool
    monkeypatch.setitem(sys.modules, "psycopg_pool", mock_psycopg_pool)

    pool = runtime.PsycopgConnectionPool("fake")

    pool.close()
    pool.close()

    # Underlying pool close should be called exactly once
    mock_pool.close.assert_called_once()


def test_auth_store_uses_provider_if_supplied():
    mock_provider = MagicMock()
    mock_conn = MagicMock()
    mock_provider.connection.return_value = mock_conn

    with patch("backend.api.services.auth_postgres._connect") as mock_fallback, patch("backend.api.services.auth_postgres.ensure_schema"):
        store = PostgresAuthStore("fake", provider=mock_provider)

        # internal _initialize should have used it
        mock_provider.connection.assert_called()
        mock_fallback.assert_not_called()

        conn = store._connection()
        assert conn is mock_conn


def test_document_store_uses_provider_if_supplied():
    mock_provider = MagicMock()
    mock_conn = MagicMock()
    mock_provider.connection.return_value = mock_conn

    with patch.object(PostgresJsonDocumentStore, "_ensure_table"):
        store = PostgresJsonDocumentStore("fake", "test", provider=mock_provider)

        conn = store._connect()
        assert conn is mock_conn
