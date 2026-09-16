from __future__ import annotations

from ..contracts import Evidence, InsightItem, InsightsResponse
from .decision_signals import rank_decision_signals
from .onboarding import get_dataset
from .overview import build_overview
from .session import scope_label


def _from_overview(dataset_id: str, scope=None) -> InsightsResponse:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")
    overview = build_overview(dataset_id, scope=scope)
    ranked = rank_decision_signals(overview, limit=8)
    ranked_ids = {signal.signal_id for signal in ranked}
    items: list[InsightItem] = []

    # Reuse the validated Overview insight engine so Insights cannot drift
    # from the metrics and evidence already shown to the user.
    by_id = {insight.id: insight for insight in [*overview.attention, *overview.opportunities]}
    for signal in ranked:
        insight = by_id[signal.signal_id]
        items.append(
            InsightItem(
                id=insight.id,
                kind=signal.kind,
                severity=insight.severity,
                title=insight.title,
                what_changed=insight.summary,
                why_it_matters=insight.why_it_matters,
                recommendation=insight.recommendation,
                metric=insight.evidence.metric,
                value=insight.evidence.value,
                display_value=signal.display_value,
                evidence=insight.evidence,
                priority_score=signal.priority_score,
                impact_score=signal.impact_score,
                urgency_score=signal.urgency_score,
                evidence_score=signal.evidence_score,
            )
        )

    # Promote only validated period-over-period KPI movements into Insights.
    # Changes remain visible after higher-value risk/opportunity signals, but
    # are never allowed to displace a ranked risk/opportunity signal.
    for metric in overview.metrics:
        if metric.delta_pct is None:
            continue
        movement_id = f"movement-{metric.id}"
        if movement_id in ranked_ids:
            continue
        direction = "increased" if metric.delta_pct >= 0 else "decreased"
        label = metric.label
        title = f"{label} {direction} {abs(metric.delta_pct):.1f}%"
        items.append(
            InsightItem(
                id=movement_id,
                kind="change",
                severity="info" if abs(metric.delta_pct) < 10 else "medium",
                title=title,
                what_changed=f"{label} moved {abs(metric.delta_pct):.1f}% ({metric.delta_label or 'comparison period'}).",
                why_it_matters=f"The current {label.lower()} differs from the validated comparison period.",
                recommendation="Investigate the driver breakdown before changing commercial plans.",
                metric=metric.id,
                value=metric.value,
                display_value=metric.display_value,
                evidence=metric.evidence,
            )
        )

    return InsightsResponse(
        dataset_id=summary.dataset_id,
        business_model=summary.business_model,
        business_model_label=summary.business_model_label,
        scope_label=scope_label(scope) if scope is not None else "All data",
        headline="What matters right now",
        summary="Validated risks and opportunities are ranked by decision priority; changes remain grounded in the same evidence engine.",
        insights=items[:8],
    )


def _display(value: float | None, metric: str) -> str:
    if value is None:
        return "—"
    if metric in {"churn", "win_rate", "return_rate", "customer_revenue_share", "weighted_pipeline_share", "product_revenue_share"} or "share" in metric:
        return f"{value:.1f}%"
    if metric in {"hours"}:
        return f"{value:,.0f}"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value/1_000:.1f}K"
    return f"${value:,.0f}"


def build_insights(dataset_id: str, scope=None) -> InsightsResponse:
    return _from_overview(dataset_id, scope=scope)
