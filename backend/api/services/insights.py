from __future__ import annotations

from ..contracts import Evidence, InsightItem, InsightsResponse
from .onboarding import get_dataset
from .overview import build_overview
from .session import scope_label


def _from_overview(dataset_id: str, scope=None) -> InsightsResponse:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")
    overview = build_overview(dataset_id, scope=scope)
    items: list[InsightItem] = []

    # Reuse the validated Overview insight engine so Insights cannot drift
    # from the metrics and evidence already shown to the user.
    for insight in overview.attention:
        items.append(
            InsightItem(
                id=insight.id,
                kind="risk",
                severity=insight.severity,
                title=insight.title,
                what_changed=insight.summary,
                why_it_matters=insight.why_it_matters,
                recommendation=insight.recommendation,
                metric=insight.evidence.metric,
                value=insight.evidence.value,
                display_value=_display(insight.evidence.value, insight.evidence.metric),
                evidence=insight.evidence,
            )
        )
    for insight in overview.opportunities:
        items.append(
            InsightItem(
                id=insight.id,
                kind="opportunity",
                severity=insight.severity,
                title=insight.title,
                what_changed=insight.summary,
                why_it_matters=insight.why_it_matters,
                recommendation=insight.recommendation,
                metric=insight.evidence.metric,
                value=insight.evidence.value,
                display_value=_display(insight.evidence.value, insight.evidence.metric),
                evidence=insight.evidence,
            )
        )

    # Promote only validated period-over-period KPI movements into Insights.
    for metric in overview.metrics:
        if metric.delta_pct is None:
            continue
        direction = "increased" if metric.delta_pct >= 0 else "decreased"
        label = metric.label
        title = f"{label} {direction} {abs(metric.delta_pct):.1f}%"
        items.append(
            InsightItem(
                id=f"movement-{metric.id}",
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

    # Deterministic priority order: risks first, then changes, then opportunities.
    rank = {"high": 0, "medium": 1, "info": 2}
    items.sort(key=lambda x: (0 if x.kind == "risk" else 1 if x.kind == "change" else 2, rank.get(x.severity, 3)))
    return InsightsResponse(
        dataset_id=summary.dataset_id,
        business_model=summary.business_model,
        business_model_label=summary.business_model_label,
        scope_label=scope_label(scope) if scope is not None else "All data",
        headline="What matters right now",
        summary="Validated changes, risks and opportunities from the current dataset and scope.",
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
