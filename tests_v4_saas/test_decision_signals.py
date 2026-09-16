from backend.api.contracts import Evidence, OverviewInsight, OverviewResponse
from backend.api.services.decision_signals import rank_decision_signals


def _insight(
    insight_id: str,
    *,
    severity: str,
    metric: str,
    value: float | None,
    fields: list[str],
) -> OverviewInsight:
    return OverviewInsight(
        id=insight_id,
        severity=severity,
        title=insight_id,
        summary="validated summary",
        why_it_matters="validated reason",
        recommendation="validated action",
        evidence=Evidence(
            metric=metric,
            value=value,
            calculation="validated calculation",
            scope="All data",
            source_fields=fields,
        ),
    )


def test_rank_decision_signals_prefers_well_supported_high_risk_signal() -> None:
    overview = OverviewResponse(
        dataset_id="d1",
        business_model="sales_pipeline",
        business_model_label="Sales pipeline",
        headline="headline",
        subheadline="subheadline",
        attention=[
            _insight("high-risk", severity="high", metric="pipeline_value", value=100000, fields=["amount"]),
            _insight("medium-risk", severity="medium", metric="win_rate", value=42, fields=["stage", "amount"]),
        ],
        opportunities=[
            _insight("opportunity", severity="info", metric="stage_pipeline_value", value=50000, fields=["stage", "amount"]),
        ],
    )

    signals = rank_decision_signals(overview)

    assert [signal.signal_id for signal in signals] == ["high-risk", "medium-risk", "opportunity"]
    assert signals[0].priority_score > signals[1].priority_score
    assert signals[0].evidence_score == 100.0


def test_rank_decision_signals_uses_signal_kind_for_impact() -> None:
    overview = OverviewResponse(
        dataset_id="d1",
        business_model="sales_pipeline",
        business_model_label="Sales pipeline",
        headline="headline",
        subheadline="subheadline",
        attention=[
            _insight("medium-attention", severity="medium", metric="pipeline_value", value=100000, fields=["amount"]),
        ],
    )

    signal = rank_decision_signals(overview)[0]

    assert signal.kind == "risk"
    assert signal.impact_score == 100.0


def test_rank_decision_signals_never_invents_empty_signals() -> None:
    overview = OverviewResponse(
        dataset_id="d1",
        business_model="sales_pipeline",
        business_model_label="Sales pipeline",
        headline="headline",
        subheadline="subheadline",
    )

    assert rank_decision_signals(overview) == []


def test_rank_decision_signals_honors_limit_and_positive_limit_only() -> None:
    insights = [
        _insight(f"risk-{i}", severity="medium", metric="pipeline_value", value=float(i), fields=["amount"])
        for i in range(5)
    ]
    overview = OverviewResponse(
        dataset_id="d1",
        business_model="sales_pipeline",
        business_model_label="Sales pipeline",
        headline="headline",
        subheadline="subheadline",
        attention=insights,
    )

    assert len(rank_decision_signals(overview, limit=2)) == 2
    assert rank_decision_signals(overview, limit=0) == []
    assert rank_decision_signals(overview, limit=-1) == []
