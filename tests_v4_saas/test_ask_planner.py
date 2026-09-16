from backend.api.contracts import Evidence, OverviewMetric, OverviewResponse
from backend.api.services.ask_planner import build_plan


def _overview(*metrics: str) -> OverviewResponse:
    return OverviewResponse(
        dataset_id="d1",
        business_model="sales_pipeline",
        business_model_label="Sales pipeline",
        headline="headline",
        subheadline="subheadline",
        metrics=[
            OverviewMetric(
                id=metric,
                label=metric.replace("_", " ").title(),
                value=100.0,
                display_value="$100",
                evidence=Evidence(
                    metric=metric,
                    value=100.0,
                    calculation="validated calculation",
                    scope="All data",
                    source_fields=["amount"],
                ),
            )
            for metric in metrics
        ],
    )


def test_plan_direct_metric_selects_validated_metric() -> None:
    plan = build_plan("What is weighted pipeline?", "sales_pipeline", _overview("weighted_forecast", "win_rate"))

    assert plan.intent == "metric"
    assert plan.metric == "weighted_forecast"
    assert plan.supported is True


def test_plan_ranking_selects_validated_dimension_and_direction() -> None:
    plan = build_plan(
        "Which stage has the highest pipeline?",
        "sales_pipeline",
        _overview("pipeline_value", "win_rate"),
        validated_dimensions=["stage", "salesperson"],
    )

    assert plan.intent == "ranking"
    assert plan.metric == "pipeline_value"
    assert plan.dimension == "stage"
    assert plan.direction == "highest"
    assert plan.supported is True


def test_plan_lowest_ranking_is_explicit() -> None:
    plan = build_plan(
        "Which salesperson has the lowest win rate?",
        "sales_pipeline",
        _overview("pipeline_value", "win_rate"),
        validated_dimensions=["stage", "salesperson"],
    )

    assert plan.intent == "ranking"
    assert plan.metric == "win_rate"
    assert plan.dimension == "salesperson"
    assert plan.direction == "lowest"


def test_plan_causal_question_uses_validated_metric_when_present() -> None:
    plan = build_plan("Why is the win rate low?", "sales_pipeline", _overview("win_rate"))

    assert plan.intent == "causal"
    assert plan.metric == "win_rate"
    assert plan.supported is True


def test_plan_refuses_unvalidated_ranking_without_dimension() -> None:
    plan = build_plan(
        "Which customer has the highest pipeline?",
        "sales_pipeline",
        _overview("pipeline_value"),
        validated_dimensions=["stage"],
    )

    assert plan.intent == "ranking"
    assert plan.supported is False
    assert plan.dimension is None
    assert "validated dimension" in plan.reason


def test_plan_refuses_ranking_when_no_validated_dimensions_are_available() -> None:
    plan = build_plan(
        "Which stage has the highest pipeline?",
        "sales_pipeline",
        _overview("pipeline_value"),
        validated_dimensions=[],
    )

    assert plan.intent == "ranking"
    assert plan.supported is False
    assert plan.dimension is None


def test_plan_refuses_metric_not_exposed_by_overview() -> None:
    plan = build_plan("What is ARR?", "subscription", _overview("mrr"))

    assert plan.intent == "unsupported"
    assert plan.supported is False


def test_plan_marks_evidence_requests_without_changing_execution_intent() -> None:
    plan = build_plan("Show the calculation and evidence for pipeline", "sales_pipeline", _overview("pipeline_value"))

    assert plan.intent == "metric"
    assert plan.metric == "pipeline_value"
    assert plan.evidence_requested is True
