import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.api import main
from backend.api import runtime_persistence

@pytest.fixture
def clean_state():
    # Reset app state
    main.app_state.lifecycle = main.LifecycleState.STARTING
    yield
    main.app_state.lifecycle = main.LifecycleState.STARTING

def test_health_is_cheap_and_static(clean_state):
    # No mocked provider or anything, should just return 200
    with TestClient(main.app) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

def test_readiness_lifecycle_external_success(monkeypatch, clean_state):
    object.__setattr__(main.settings, "persistence_mode", "external")

    mock_provider = MagicMock()
    monkeypatch.setattr(runtime_persistence, "_provider", mock_provider)

    # Before startup
    client = TestClient(main.app)
    main.app_state.lifecycle = main.LifecycleState.STARTING
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 503
    assert resp.json() == {"status": "not_ready", "reason": "starting"}

    # After startup
    main.app_state.lifecycle = main.LifecycleState.READY
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "reason": None}
    mock_provider.check.assert_called_once()

    # Degraded DB
    class DatabaseError(Exception):
        pass
    mock_provider.check.side_effect = DatabaseError("connection lost")
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 503
    # M: response contains no traceback/DSN/credentials/SQL
    assert resp.json() == {"status": "not_ready", "reason": "database_down"}

    # Recovered DB
    mock_provider.check.side_effect = None
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "reason": None}

    # Shutting down
    main.app_state.lifecycle = main.LifecycleState.SHUTTING_DOWN
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 503
    assert resp.json() == {"status": "not_ready", "reason": "shutting_down"}


def test_readiness_lifecycle_local_mode(monkeypatch, clean_state):
    object.__setattr__(main.settings, "persistence_mode", "local")

    # No DB provider mocked
    main.app_state.lifecycle = main.LifecycleState.READY
    client = TestClient(main.app)
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "reason": None}


def test_no_local_fallback_in_external_mode(monkeypatch, clean_state):
    object.__setattr__(main.settings, "persistence_mode", "external")
    monkeypatch.setattr(runtime_persistence, "_provider", None)

    main.app_state.lifecycle = main.LifecycleState.READY
    client = TestClient(main.app)
    resp = client.get("/api/v1/ready")

    # Should not fall back to local (status 200), must fail 503
    assert resp.status_code == 503
    assert resp.json() == {"status": "not_ready", "reason": "provider_missing"}

def test_repeated_shutdown_safe(monkeypatch, clean_state):
    object.__setattr__(main.settings, "persistence_mode", "local")

    # Simulate multiple shutdown calls manually
    with TestClient(main.app) as client:
        pass # this triggers lifespan shutdown

    # Do it again directly
    from backend.api.runtime_persistence import reset_runtime_persistence
    reset_runtime_persistence()
    reset_runtime_persistence()
    # It shouldn't crash
