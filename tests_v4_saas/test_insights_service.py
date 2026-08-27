from pathlib import Path

import pytest

from backend.api.services.insights import build_insights
from backend.api.services.onboarding import onboard


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def _load(name: str):
    path = SAMPLES / name
    if not path.exists():
        pytest.fail(f"Sample dataset is missing: {path}")
    with path.open("rb") as fh:
        return onboard(name, fh)


def test_retail_insights_are_evidence_backed():
    summary = _load("retail.csv")
    response = build_insights(summary.dataset_id)

    assert response.dataset_id == summary.dataset_id
    assert response.business_model == "transactional_sales"
    assert response.insights
    assert all(item.evidence.calculation for item in response.insights)
    assert all(item.evidence.scope == "All data" for item in response.insights)


def test_pipeline_insights_are_pipeline_specific():
    summary = _load("pipeline.csv")
    response = build_insights(summary.dataset_id)

    assert response.business_model == "sales_pipeline"
    assert response.insights
    assert any("pipeline" in item.metric for item in response.insights)
    assert all(item.evidence.calculation for item in response.insights)


def test_subscription_insights_are_supported():
    summary = _load("subscription.csv")
    response = build_insights(summary.dataset_id)

    assert response.business_model == "subscription"
    assert response.insights
    assert any(item.metric in {"churn", "customer_mrr"} for item in response.insights)
    assert all(item.evidence.calculation for item in response.insights)


def test_services_insights_are_supported():
    summary = _load("services.csv")
    response = build_insights(summary.dataset_id)

    assert response.business_model == "services"
    assert response.insights
    assert any(item.metric in {"client_billings", "hours"} for item in response.insights)
    assert all(item.evidence.calculation for item in response.insights)


def test_unknown_dataset_is_rejected():
    with pytest.raises(ValueError, match="Dataset not found"):
        build_insights("does-not-exist")
