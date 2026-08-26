from io import BytesIO
from pathlib import Path

from backend.api.services.onboarding import onboard
from backend.api.services.overview import build_overview

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_retail_overview_is_deterministic_and_has_evidence():
    summary = onboard("retail.csv", BytesIO((SAMPLES / "retail.csv").read_bytes()))
    overview = build_overview(summary.dataset_id)
    assert overview.business_model == "transactional_sales"
    assert [m.id for m in overview.metrics][:3] == ["revenue", "orders", "aov"]
    assert all(metric.evidence.source_fields for metric in overview.metrics)
    assert any(item.id == "return-rate-risk" for item in overview.attention)


def test_pipeline_overview_uses_pipeline_metrics():
    summary = onboard("pipeline.csv", BytesIO((SAMPLES / "pipeline.csv").read_bytes()))
    overview = build_overview(summary.dataset_id)
    assert overview.business_model == "sales_pipeline"
    assert {m.id for m in overview.metrics} >= {"pipeline_value", "weighted_forecast", "win_rate"}
    assert any(item.id == "pipeline-stage" for item in overview.opportunities)


def test_subscription_overview_derives_arr_from_mrr():
    summary = onboard("subscription.csv", BytesIO((SAMPLES / "subscription.csv").read_bytes()))
    overview = build_overview(summary.dataset_id)
    metric_map = {m.id: m for m in overview.metrics}
    assert metric_map["mrr"].value == 800
    assert metric_map["arr"].value == 9600
    assert metric_map["arr"].evidence.calculation == "MRR × 12"


def test_services_overview_uses_billing_and_hours():
    summary = onboard("services.csv", BytesIO((SAMPLES / "services.csv").read_bytes()))
    overview = build_overview(summary.dataset_id)
    assert overview.business_model == "services"
    assert {m.id for m in overview.metrics} >= {"billings", "hours", "billing_per_hour"}
