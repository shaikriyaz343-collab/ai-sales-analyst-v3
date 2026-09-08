import logging
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

import backend.api.main as main_module
from backend.api.config import settings
import psycopg
try:
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    class BotoCoreError(Exception): pass
    class ClientError(Exception): pass

app = main_module.app

# --- Test routes registered once at import time. ---
# They read settings.database_url / settings.object_store_secret_key at
# request time via the name "settings" that lives on main_module, so the
# per-test fixture below controls what they see.

@app.get("/api/v1/trigger_error/db")
def trigger_error_db():
    raise psycopg.OperationalError("connection failed to " + str(main_module.settings.database_url))

@app.get("/api/v1/trigger_error/boto")
def trigger_error_boto():
    raise ClientError({'Error': {'Message': 'storage failed for key ' + str(main_module.settings.object_store_secret_key), 'Code': 'Unknown'}}, 'operation')

@app.get("/api/v1/trigger_error/value")
def trigger_error_value():
    raise ValueError("unexpected failure password=" + str(main_module.settings.database_url))

@app.get("/api/v1/trigger_error/http")
def trigger_error_http():
    from fastapi import HTTPException
    raise HTTPException(status_code=403, detail="Forbidden area")


class LogCaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(self.format(record))


@pytest.fixture(autouse=True)
def fake_settings(monkeypatch):
    """Provide an isolated Settings object with known fake secrets.

    Patches the module-level 'settings' reference on backend.api.main so that
    both the test route handlers and the _sanitize_log redaction logic read the
    same fake values.  The original Settings object is never mutated.
    """
    test_settings = replace(
        settings,
        database_url="postgresql://secret_db_url",
        object_store_secret_key="secret_aws_key",
    )
    monkeypatch.setattr(main_module, "settings", test_settings)
    yield test_settings


@pytest.fixture(autouse=True)
def setup_logging():
    logger = logging.getLogger("ai_sales_analyst.errors")
    handler = LogCaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)
    yield handler
    logger.removeHandler(handler)


client = TestClient(app, raise_server_exceptions=False)


def test_postgresql_operational_error(fake_settings, setup_logging):
    response = client.get("/api/v1/trigger_error/db")
    assert response.status_code == 503
    assert response.json() == {"detail": "Service Unavailable - Database connection failed."}

    assert len(setup_logging.messages) == 1
    log_text = setup_logging.messages[0]
    assert "Database dependency failure" in log_text
    assert fake_settings.database_url not in log_text
    assert "***REDACTED***" in log_text

def test_boto_core_error(fake_settings, setup_logging):
    response = client.get("/api/v1/trigger_error/boto")
    assert response.status_code == 503
    assert response.json() == {"detail": "Service Unavailable - Object storage failed."}

    log_text = setup_logging.messages[0]
    assert "Object storage client failure" in log_text
    assert fake_settings.object_store_secret_key not in log_text
    assert "***REDACTED***" in log_text

def test_unexpected_value_error(fake_settings, setup_logging):
    response = client.get("/api/v1/trigger_error/value")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}

    log_text = setup_logging.messages[0]
    assert "Unexpected internal error" in log_text
    assert "ValueError: unexpected failure" in log_text
    assert fake_settings.database_url not in log_text
    assert "***REDACTED***" in log_text

def test_existing_http_exception_unchanged(setup_logging):
    response = client.get("/api/v1/trigger_error/http")
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden area"}
    assert len(setup_logging.messages) == 0

def test_validation_error_unchanged(setup_logging):
    response = client.post("/api/v1/auth/login", json={"missing": "email"})
    assert response.status_code == 422
    assert len(setup_logging.messages) == 0
