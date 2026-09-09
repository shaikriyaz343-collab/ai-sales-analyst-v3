import pytest
from pathlib import Path
import sys
import pandas as pd
import inspect
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api.main import app
from backend.api.services import explore
from backend.api.services.onboarding import onboard
import schema_profiler_v2

client = TestClient(app)
SAMPLES = ROOT / "samples"

def _upload(name: str):
    path = SAMPLES / name
    with path.open("rb") as fh:
        return onboard(name, fh)

def test_explore_performs_single_physical_dataframe_load(monkeypatch):
    summary = _upload("retail.csv")

    original_read_csv = pd.read_csv
    call_count = 0

    def mock_read_csv(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_read_csv(*args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", mock_read_csv)

    result = explore.build_explore(summary.dataset_id, "revenue", "product")

    assert call_count == 1

    assert result.metric == "revenue"
    assert result.dimension == "product"

def test_health_returns_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_ready_remains_synchronous():
    from backend.api.main import ready
    assert not inspect.iscoroutinefunction(ready), "/ready must remain synchronous"

    response = client.get("/api/v1/ready")
    assert response.status_code in (200, 503)

def test_duplicate_load_optimization_does_not_mutate():
    path = SAMPLES / "retail.csv"
    data1 = schema_profiler_v2.load_dataframe(path)
    data2 = data1.copy(deep=True)
    profile = schema_profiler_v2.profile_dataframe(data1)
    pd.testing.assert_frame_equal(data1, data2)
