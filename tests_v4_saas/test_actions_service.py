from pathlib import Path

import pytest

from backend.api.services.onboarding import onboard
from backend.api.services.actions import build_actions

SAMPLES = Path(__file__).parents[1] / "samples"


@pytest.mark.parametrize(
    "filename, model, expected_owner",
    [
        ("retail.csv", "transactional_sales", "Sales / Operations"),
        ("pipeline.csv", "sales_pipeline", "Sales Leadership"),
        ("subscription.csv", "subscription", "Customer Success"),
        ("services.csv", "services", "Services Leadership"),
    ],
)
def test_actions_are_business_model_specific(tmp_path, filename, model, expected_owner, monkeypatch):
    import backend.api.services.onboarding as onboarding
    import backend.api.services.overview as overview

    monkeypatch.setattr(onboarding, "STORAGE", tmp_path)
    monkeypatch.setattr(overview, "STORAGE", tmp_path)
    with (SAMPLES / filename).open("rb") as handle:
        summary = onboard(filename, handle)

    response = build_actions(summary.dataset_id)
    assert response.business_model == model
    assert response.actions
    assert all(item.owner == expected_owner for item in response.actions)
    assert all(item.source_insight_id for item in response.actions)
    assert all(item.evidence.calculation for item in response.actions)


def test_actions_reuse_validated_overview_insights(monkeypatch, tmp_path):
    import backend.api.services.onboarding as onboarding
    import backend.api.services.overview as overview

    monkeypatch.setattr(onboarding, "STORAGE", tmp_path)
    monkeypatch.setattr(overview, "STORAGE", tmp_path)
    with (SAMPLES / "retail.csv").open("rb") as handle:
        summary = onboard("retail.csv", handle)

    response = build_actions(summary.dataset_id)
    source_ids = {action.source_insight_id for action in response.actions}
    assert "customer-concentration" in source_ids or "return-rate-risk" in source_ids or "top-product" in source_ids


def test_empty_dataset_produces_no_actions(tmp_path, monkeypatch):
    # Build an empty but structurally valid retail-like CSV and verify no fabricated actions are emitted.
    import backend.api.services.onboarding as onboarding
    import backend.api.services.overview as overview

    monkeypatch.setattr(onboarding, "STORAGE", tmp_path)
    monkeypatch.setattr(overview, "STORAGE", tmp_path)
    empty = tmp_path / "empty.csv"
    empty.write_text("OrderID,OrderDate,CustomerName,ProductName,Quantity,UnitPrice,TotalAmount,Region,Discount %,Return Status,PaymentMethod\n", encoding="utf-8")
    with empty.open("rb") as handle:
        summary = onboard("empty.csv", handle)
    response = build_actions(summary.dataset_id)
    assert response.actions == []
