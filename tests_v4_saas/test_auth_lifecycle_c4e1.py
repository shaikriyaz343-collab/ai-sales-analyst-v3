import pytest
import sys
from dataclasses import replace
from unittest.mock import patch, MagicMock

from backend.api.config import settings


def test_external_auth_import_does_not_initialize_postgres(monkeypatch):
    import subprocess
    import sys

    # We run a small script in a subprocess to ensure true isolation
    # and prove that just importing auth.py with external mode doesn't connect.
    script = """
import sys
import unittest.mock as mock

with mock.patch("psycopg.connect") as mock_connect:
    import backend.api.config
    backend.api.config.settings = mock.MagicMock()
    backend.api.config.settings.persistence_mode = "external"

    import backend.api.services.auth

    # Check that psycopg.connect wasn't called during import
    mock_connect.assert_not_called()
"""

    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, f"Import test failed:\n{result.stderr}"


def test_lifecycle_initializes_external_auth(monkeypatch):
    import asyncio

    from backend.api.main import app, lifespan
    import backend.api.main as main_module
    import backend.api.runtime_persistence as runtime_persistence
    import backend.api.services.auth as auth

    # --- 1. Create an isolated Settings object; never mutate the global one ---
    test_settings = replace(
        settings,
        persistence_mode="external",
        database_url="postgresql://fake",
        object_store_bucket="fake-bucket",
        object_store_region="fake-region",
    )

    # Patch every module reference that reads settings during the lifespan path
    monkeypatch.setattr(main_module, "settings", test_settings)
    monkeypatch.setattr(runtime_persistence, "settings", test_settings)
    monkeypatch.setattr(auth, "settings", test_settings)
    monkeypatch.setattr("backend.api.services.auth_postgres.settings", test_settings)

    # --- 2. Deterministically clear stale runtime state before the test ---
    runtime_persistence.reset_runtime_persistence()
    auth.reset_external_auth()

    events = []

    original_start = runtime_persistence.start_runtime_persistence
    def mock_start():
        events.append("start_runtime_persistence")
        original_start()

    original_set = auth.set_external_auth
    def mock_set(store):
        events.append("set_external_auth")
        assert store.provider is not None
        assert store.provider is runtime_persistence._provider
        original_set(store)

    monkeypatch.setattr(runtime_persistence, "start_runtime_persistence", mock_start)
    monkeypatch.setattr(auth, "set_external_auth", mock_set)
    monkeypatch.setattr("backend.api.services.auth_postgres.ensure_schema", MagicMock())

    mock_pool = MagicMock()
    mock_pool_instance = MagicMock()
    mock_pool.return_value = mock_pool_instance
    monkeypatch.setattr(runtime_persistence, "PsycopgConnectionPool", mock_pool)

    async def run_lifespan():
        async with lifespan(app):
            pass

    asyncio.run(run_lifespan())

    # start_runtime_persistence must be called BEFORE set_external_auth
    assert events == ["start_runtime_persistence", "set_external_auth"]
