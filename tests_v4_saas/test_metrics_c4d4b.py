import json
import logging
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.api.main import app
from backend.api import telemetry
from fastapi import APIRouter

# Add dummy routes to trigger exceptions properly
dummy_router = APIRouter()

@dummy_router.get("/dummy_500")
def dummy_500():
    raise Exception("Test 500 error")

@dummy_router.get("/dummy_db_pool_timeout")
def dummy_db_pool_timeout():
    import psycopg_pool
    raise psycopg_pool.PoolTimeout("Test DB Error")

@dummy_router.get("/dummy_db_error")
def dummy_db_error():
    import psycopg
    raise psycopg.OperationalError("Test DB Error")

@dummy_router.get("/dummy_s3_error")
def dummy_s3_error():
    from botocore.exceptions import BotoCoreError
    raise BotoCoreError()

app.include_router(dummy_router)

class EagerJSONHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []
        self.setFormatter(telemetry.MetricJSONFormatter())

    def emit(self, record):
        if hasattr(record, "metric_payload"):
            self.records.append(json.loads(self.format(record)))

@pytest.fixture
def metric_log():
    handler = EagerJSONHandler()
    logger = logging.getLogger("ai_sales_analyst.metrics")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    old_handlers = logger.handlers.copy()
    yield handler
    logger.handlers = old_handlers

def test_telemetry_version_and_exact_schema(metric_log):
    telemetry.emit_metric("http_requests_total", 1, {"method": "GET", "route": "/api/v1/health", "status_code": 200})
    assert len(metric_log.records) == 1
    record = metric_log.records[0]

    assert record["telemetry_version"] == 1
    assert record["event_type"] == "metric"
    assert record["metric_name"] == "http_requests_total"
    assert record["metric_type"] == "counter"
    assert record["value"] == 1
    assert record["unit"] == "count"
    assert record["labels"] == {"method": "GET", "route": "/api/v1/health", "status_code": 200}

def test_registry_rejects_unknown_metric():
    with pytest.raises(ValueError, match="Unknown metric"):
        telemetry.emit_metric("unknown_metric", 1, {})

def test_registry_rejects_unknown_labels():
    with pytest.raises(ValueError, match="Unknown label key"):
        telemetry.emit_metric("http_requests_total", 1, {"method": "GET", "route": "/foo", "status_code": 200, "unknown_label": "bad"})

def test_registry_rejects_forbidden_labels():
    for forbidden in telemetry.FORBIDDEN_LABELS:
        with pytest.raises(ValueError, match="Forbidden metric label"):
            telemetry.emit_metric("http_requests_total", 1, {"method": "GET", "route": "/foo", "status_code": 200, forbidden: "value"})

def test_registry_rejects_unbounded_enum():
    with pytest.raises(ValueError, match="Invalid value"):
        telemetry.emit_metric("auth_failures_total", 1, {"route": "/api", "reason": "unsupported_reason"})

def test_http_metrics_emission(metric_log):
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    reqs = [r for r in metric_log.records if r["metric_name"] == "http_requests_total"]
    assert len(reqs) == 1
    assert reqs[0]["labels"]["status_code"] == 200
    assert reqs[0]["labels"]["route"] == "/api/v1/health"

    durs = [r for r in metric_log.records if r["metric_name"] == "http_request_duration_seconds"]
    assert len(durs) == 1

    fives = [r for r in metric_log.records if r["metric_name"] == "http_5xx_total"]
    assert len(fives) == 0

def test_http_5xx_metric_emission(metric_log):
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/dummy_500")
    assert response.status_code == 500

    fives = [r for r in metric_log.records if r["metric_name"] == "http_5xx_total"]
    assert len(fives) == 1
    assert fives[0]["labels"]["status_code"] == 500

    reqs = [r for r in metric_log.records if r["metric_name"] == "http_requests_total"]
    assert len(reqs) == 1
    assert reqs[0]["labels"]["status_code"] == 500

def test_auth_failure_metric(metric_log):
    client = TestClient(app)
    response = client.get("/api/v1/workspaces")
    assert response.status_code == 401

    auth_fails = [r for r in metric_log.records if r["metric_name"] == "auth_failures_total"]
    assert len(auth_fails) == 1
    assert auth_fails[0]["labels"]["route"] == "/api/v1/workspaces"
    assert auth_fails[0]["labels"]["reason"] == "missing_token"

def test_rate_limit_metric(metric_log):
    client = TestClient(app)
    with patch("backend.api.main.consume_rate_limit", return_value=False):
        response = client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "abc"})
        assert response.status_code == 429

    rate_limits = [r for r in metric_log.records if r["metric_name"] == "rate_limit_hits_total"]
    assert len(rate_limits) == 1
    assert rate_limits[0]["labels"]["route"] == "/api/v1/auth/login"

def test_database_failures_metrics(metric_log):
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/dummy_db_error")

    db_fails = [r for r in metric_log.records if r["metric_name"] == "database_failures_total"]
    assert len(db_fails) == 1
    assert db_fails[0]["labels"]["operation"] == "query"
    assert db_fails[0]["labels"]["failure_type"] == "connection"

def test_database_pool_timeout_metrics(metric_log, monkeypatch):
    import sys
    import psycopg
    from unittest.mock import MagicMock

    # Real psycopg_pool.PoolTimeout inherits from psycopg.OperationalError.
    # This must match so FastAPI dispatches to psycopg_operational_exception_handler.
    class MockPoolTimeout(psycopg.OperationalError):
        pass

    mock_psycopg_pool = MagicMock()
    mock_psycopg_pool.PoolTimeout = MockPoolTimeout
    monkeypatch.setitem(sys.modules, "psycopg_pool", mock_psycopg_pool)

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/dummy_db_pool_timeout")

    db_fails = [r for r in metric_log.records if r["metric_name"] == "database_pool_timeouts_total"]
    assert len(db_fails) == 1
    assert db_fails[0]["labels"]["pool_name"] == "default"

def test_object_store_failures_metrics(metric_log):
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/dummy_s3_error")

    s3_fails = [r for r in metric_log.records if r["metric_name"] == "object_store_failures_total"]
    assert len(s3_fails) == 1
    assert s3_fails[0]["labels"]["operation"] == "read"
    assert s3_fails[0]["labels"]["failure_type"] == "client_error"

def test_migration_status(metric_log):
    from backend.api.migrations.auth_sqlite_to_postgres import migrate_sqlite_to_postgres
    with patch("backend.api.migrations.auth_sqlite_to_postgres.migrate_sqlite_to_target", return_value=None):
        with patch("backend.api.migrations.auth_sqlite_to_postgres.PostgresMigrationTarget"):
            migrate_sqlite_to_postgres("dummy_source", "dummy_db", dry_run=False, verify=False)

    mig_status = [r for r in metric_log.records if r["metric_name"] == "migration_status"]
    assert len(mig_status) == 1
    assert mig_status[0]["labels"]["target_version"] == "v4_postgres"
    assert mig_status[0]["labels"]["status"] == "success"
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api import telemetry
from backend.api.migrations.auth_sqlite_to_postgres import migrate_sqlite_to_postgres
import psycopg

def test_safe_emit_metric_never_raises():
    # Calling safe_emit_metric with forbidden label -> should not raise Exception
    telemetry.safe_emit_metric("http_requests_total", 1, {"route": "/foo", "status_code": 200, "request_id": "abc"})
    # If it reached here, it didn't raise!

def test_auth_failure_remains_401_even_if_telemetry_fails():
    client = TestClient(app)
    with patch("backend.api.telemetry.emit_metric", side_effect=ValueError("Boom")):
        response = client.get("/api/v1/workspaces")
        assert response.status_code == 401

def test_rate_limit_remains_429_even_if_telemetry_fails():
    client = TestClient(app)
    with patch("backend.api.main.consume_rate_limit", return_value=False):
        with patch("backend.api.telemetry.emit_metric", side_effect=ValueError("Boom")):
            response = client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "abc"})
            assert response.status_code == 429

def test_db_dependency_remains_503_even_if_telemetry_fails():
    client = TestClient(app, raise_server_exceptions=False)
    with patch("backend.api.telemetry.emit_metric", side_effect=ValueError("Boom")):
        response = client.get("/dummy_db_error")
        assert response.status_code == 503

def test_unexpected_error_remains_500_even_if_telemetry_fails():
    client = TestClient(app, raise_server_exceptions=False)
    with patch("backend.api.telemetry.emit_metric", side_effect=ValueError("Boom")):
        response = client.get("/dummy_500")
        assert response.status_code == 500

def test_middleware_contextvars_always_reset_when_telemetry_fails():
    client = TestClient(app)
    # mock token logic to just test middleware
    with patch("backend.api.telemetry.emit_metric", side_effect=ValueError("Boom")):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
    assert telemetry.request_id_var.get() is None

def test_migration_success_remains_success_when_telemetry_fails():
    with patch("backend.api.migrations.auth_sqlite_to_postgres.migrate_sqlite_to_target", return_value="Result!"):
        with patch("backend.api.migrations.auth_sqlite_to_postgres.PostgresMigrationTarget"):
            with patch("backend.api.telemetry.emit_metric", side_effect=ValueError("Boom")):
                res = migrate_sqlite_to_postgres("dummy_source", "dummy_db", dry_run=False, verify=False)
                assert res == "Result!"

def test_migration_failure_remains_failure_when_telemetry_fails():
    with patch("backend.api.migrations.auth_sqlite_to_postgres.migrate_sqlite_to_target", side_effect=RuntimeError("Original Migration Error")):
        with patch("backend.api.migrations.auth_sqlite_to_postgres.PostgresMigrationTarget"):
            with patch("backend.api.telemetry.emit_metric", side_effect=ValueError("Boom")):
                with pytest.raises(RuntimeError, match="Original Migration Error"):
                    migrate_sqlite_to_postgres("dummy_source", "dummy_db", dry_run=False, verify=False)
