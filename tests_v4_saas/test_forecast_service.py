from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api.services import forecast
from backend.api.services.forecast import build_forecast
from backend.api.services.onboarding import onboard, STORAGE

SAMPLES = ROOT / "samples"


def upload(name: str):
    path = SAMPLES / name
    with path.open("rb") as handle:
        return onboard(path.name, handle)


def test_pipeline_forecast_is_explainable_and_deterministic() -> None:
    dataset = upload("pipeline.csv")
    result = build_forecast(dataset.dataset_id)

    assert result.weighted_forecast == 50500
    assert result.open_pipeline_value == 85000
    assert result.open_opportunities == 3
    assert result.has_probability is True
    assert "probability" in result.basis_note.lower()
    assert result.evidence.metric == "weighted_forecast"
    assert "Amount" in result.evidence.source_fields
    assert "Probability" in result.evidence.source_fields
    assert result.evidence.source_records == ["O2", "O4", "O5"]
    assert result.monthly_forecast
    assert all(item.evidence.source_fields for item in result.monthly_forecast)
    by_month = {item.month: item.evidence.source_records for item in result.monthly_forecast}
    assert by_month["2026-02"] == ["O2"]
    assert by_month["2026-03"] == ["O4", "O5"]


def test_forecast_materializes_from_runtime_object_store(monkeypatch, tmp_path):
    dataset = upload("pipeline.csv")
    local_object = STORAGE / f"{dataset.dataset_id}.csv"
    assert local_object.exists()

    class StubObjectStore:
        def path_for(self, key: str) -> Path:
            assert key == f"{dataset.dataset_id}.csv"
            return local_object

    monkeypatch.setattr(forecast, "STORAGE", tmp_path / "not-the-object-store")
    monkeypatch.setattr(forecast, "runtime_object_store", lambda *, local_root: StubObjectStore())

    result = build_forecast(dataset.dataset_id)
    assert result.weighted_forecast == 50500


def test_forecast_rejects_non_pipeline_dataset() -> None:
    dataset = upload("retail.csv")
    try:
        build_forecast(dataset.dataset_id)
    except ValueError as exc:
        assert "sales-pipeline" in str(exc)
    else:
        raise AssertionError("forecast should not be available for retail data")
