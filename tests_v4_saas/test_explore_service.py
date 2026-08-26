from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api.services import explore
from backend.api.services.onboarding import onboard, STORAGE

SAMPLES = ROOT / "samples"


def _upload(name: str):
    path = SAMPLES / name
    with path.open("rb") as fh:
        return onboard(name, fh)


def test_retail_explore_is_dimension_and_metric_consistent():
    summary = _upload("retail.csv")
    result = explore.build_explore(summary.dataset_id, "revenue", "product")
    assert result.metric == "revenue"
    assert result.metric_label == "Revenue"
    assert result.dimension == "product"
    assert result.rows
    assert result.rows[0].evidence["metric"] == "revenue"
    assert result.rows[0].evidence["source_fields"]


def test_pipeline_explore_uses_pipeline_metrics_not_retail_metrics():
    summary = _upload("pipeline.csv")
    result = explore.build_explore(summary.dataset_id, "weighted_pipeline", "stage")
    assert result.metric == "weighted_pipeline"
    assert result.dimension == "stage"
    assert result.rows
    assert result.total_value is not None
    assert result.rows[0].evidence["calculation"].startswith("Weighted Pipeline")


def test_subscription_explore_supports_mrr_by_plan():
    summary = _upload("subscription.csv")
    result = explore.build_explore(summary.dataset_id, "mrr", "plan")
    assert result.metric == "mrr"
    assert result.dimension == "plan"
    assert sum(row.value for row in result.rows) == result.total_value


def test_services_explore_supports_billing_per_hour_by_service():
    summary = _upload("services.csv")
    result = explore.build_explore(summary.dataset_id, "billing_per_hour", "service")
    assert result.metric == "billing_per_hour"
    assert result.dimension == "service"
    assert result.rows
    assert all(row.value >= 0 for row in result.rows)


def test_default_explore_is_determined_by_backend_context():
    summary = _upload("retail.csv")
    result = explore.build_explore(summary.dataset_id)
    assert result.metric in {option["id"] for option in [item.model_dump() for item in result.available_metrics]}
    assert result.dimension in {option["id"] for option in [item.model_dump() for item in result.available_dimensions]}


def test_unsupported_metric_is_rejected():
    summary = _upload("pipeline.csv")
    try:
        explore.build_explore(summary.dataset_id, "return_rate", "stage")
    except ValueError as exc:
        assert "not supported" in str(exc)
    else:
        raise AssertionError("Unsupported metric should be rejected")
