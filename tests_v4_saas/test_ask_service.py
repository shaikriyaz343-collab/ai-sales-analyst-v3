from __future__ import annotations

from io import BytesIO
from pathlib import Path

from backend.api.services.onboarding import onboard
from backend.api.services.ask import answer_question

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def upload(name: str):
    path = SAMPLES / name
    with path.open("rb") as handle:
        return onboard(path.name, handle)


def test_retail_direct_metric_and_evidence() -> None:
    dataset = upload("retail.csv")
    result = answer_question(dataset.dataset_id, "What is total revenue?")
    assert result.answer.status == "answered"
    assert result.answer.evidence is not None
    assert result.answer.evidence.metric == "revenue"
    assert result.answer.evidence.value == 4180
    assert result.analytical_plan is not None
    assert result.analytical_plan["intent"] == "metric"


def test_retail_ranking_has_explore_target() -> None:
    dataset = upload("retail.csv")
    result = answer_question(dataset.dataset_id, "Which product has the highest revenue?")
    assert result.answer.status == "answered"
    assert "Phone" in result.answer.text
    assert result.explore_metric == "revenue"
    assert result.explore_dimension == "product"
    assert result.analytical_plan is not None
    assert result.analytical_plan["intent"] == "ranking"


def test_retail_change_question_uses_validated_comparison() -> None:
    dataset = upload("retail.csv")
    result = answer_question(dataset.dataset_id, "What changed in revenue?")
    assert result.answer.status == "answered"
    assert result.answer.evidence is not None
    assert result.answer.evidence.metric == "revenue"
    assert result.answer.evidence.comparison_value == 1480
    assert "increased" in result.answer.text
    assert result.analytical_plan is not None
    assert result.analytical_plan["intent"] == "change"


def test_pipeline_weighted_pipeline_is_deterministic() -> None:
    dataset = upload("pipeline.csv")
    result = answer_question(dataset.dataset_id, "What is weighted pipeline?")
    assert result.answer.status == "answered"
    assert result.answer.evidence is not None
    assert result.answer.evidence.metric == "weighted_forecast"
    assert result.answer.evidence.value == 50500


def test_subscription_unsupported_metric_is_not_guessed() -> None:
    dataset = upload("subscription.csv")
    result = answer_question(dataset.dataset_id, "What is the return rate?")
    assert result.answer.status == "unsupported"
    assert "won't guess" in result.answer.text


def test_services_billings_answer() -> None:
    dataset = upload("services.csv")
    result = answer_question(dataset.dataset_id, "What are total billings?")
    assert result.answer.status == "answered"
    assert result.answer.evidence is not None
    assert result.answer.evidence.metric == "billings"
    assert result.answer.evidence.value == 4640


def test_why_question_uses_validated_insight() -> None:
    dataset = upload("retail.csv")
    result = answer_question(dataset.dataset_id, "Why is the return rate high?")
    assert result.answer.status == "answered"
    assert result.answer.evidence is not None
    assert result.answer.evidence.metric == "return_rate"
