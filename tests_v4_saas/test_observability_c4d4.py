import asyncio
import json
import logging
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

from backend.api import main
from backend.api import telemetry

@pytest.fixture(autouse=True)
def setup_test_handlers():
    main.setup_logging()

    # Add a custom memory handler that formats records eagerly
    class EagerJSONHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.formatted_records = []
            self.setFormatter(telemetry.JSONFormatter())

        def emit(self, record):
            # Run the filter to attach context vars
            for f in self.filters:
                f.filter(record)
            # Eagerly format to JSON while context is active
            self.formatted_records.append(json.loads(self.format(record)))

    access_handler = EagerJSONHandler()
    access_handler.addFilter(telemetry.ContextFilter())
    logging.getLogger("ai_sales_analyst.access").addHandler(access_handler)

    error_handler = EagerJSONHandler()
    error_handler.addFilter(telemetry.ContextFilter())
    logging.getLogger("ai_sales_analyst.errors").addHandler(error_handler)

    yield {"access": access_handler, "errors": error_handler}

def test_request_id_missing_generated():
    client = TestClient(main.app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) == 32

def test_request_id_valid_preserved():
    client = TestClient(main.app)
    valid_id = "test-valid-id-12345"
    response = client.get("/api/v1/health", headers={"X-Request-ID": valid_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == valid_id

def test_request_id_malformed_replaced():
    client = TestClient(main.app)
    malformed = "invalid@#$%"
    response = client.get("/api/v1/health", headers={"X-Request-ID": malformed})
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id != malformed
    assert len(req_id) == 32

def test_access_log_structured_and_normalized(setup_test_handlers):
    client = TestClient(main.app)
    client.get("/api/v1/health?session_id=super_secret")

    logs = setup_test_handlers["access"].formatted_records
    access_log = next(log for log in logs if log.get("logger") == "ai_sales_analyst.access")

    assert "request_id" in access_log
    assert access_log["route"] == "/api/v1/health"
    assert "super_secret" not in json.dumps(access_log)

def test_c4d1_unexpected_exception_still_sanitized(setup_test_handlers):
    @main.app.get("/api/v1/test_c4d1_fail")
    def fail_endpoint():
        raise RuntimeError("Simulated Exception")

    client = TestClient(main.app, raise_server_exceptions=False)

    try:
        response = client.get("/api/v1/test_c4d1_fail")
    except RuntimeError:
        pass

    logs = setup_test_handlers["errors"].formatted_records
    error_log = next(log for log in logs if log.get("logger") == "ai_sales_analyst.errors")

    assert "request_id" in error_log
    assert "Unexpected internal error" in error_log["message"]
    assert "Simulated Exception" in error_log["message"]

@pytest.mark.anyio
async def test_concurrent_context_isolation():
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        req1 = client.get("/api/v1/health", headers={"X-Request-ID": "req-1"})
        req2 = client.get("/api/v1/health", headers={"X-Request-ID": "req-2"})

        res1, res2 = await asyncio.gather(req1, req2)

        assert res1.headers["X-Request-ID"] == "req-1"
        assert res2.headers["X-Request-ID"] == "req-2"

def test_uvicorn_access_logging_silenced():
    uvicorn_logger = logging.getLogger("uvicorn.access")
    assert not uvicorn_logger.propagate
