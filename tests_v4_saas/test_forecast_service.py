from pathlib import Path

from backend.api.services.forecast import build_forecast
from backend.api.services.onboarding import onboard

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def upload(name: str):
    path = SAMPLES / name
    with path.open("rb") as handle:
        return onboard(path.name, handle)


def test_pipeline_forecast_is_explainable_and_deterministic() -> None:
    dataset = upload("pipeline.csv")
    result = build_forecast(dataset.dataset_id)

    assert result.weighted_forecast == 50500
    assert result.open_pipeline_value == 65000
    assert result.open_opportunities == 3
    assert result.has_probability is True
    assert "probability" in result.basis_note.lower()
    assert result.evidence.metric == "weighted_forecast"
    assert "amount" in result.evidence.source_fields
    assert "probability" in result.evidence.source_fields
    assert result.monthly_forecast
    assert all(item.evidence.source_fields for item in result.monthly_forecast)


def test_forecast_rejects_non_pipeline_dataset() -> None:
    dataset = upload("retail.csv")
    try:
        build_forecast(dataset.dataset_id)
    except ValueError as exc:
        assert "sales-pipeline" in str(exc)
    else:
        raise AssertionError("forecast should not be available for retail data")
