from __future__ import annotations

from datetime import datetime, timezone

from ..contracts import ReportResponse
from .actions import build_actions
from .insights import build_insights
from .onboarding import get_dataset
from .overview import build_overview
from .session import scope_label


def _summary_text(overview, insights, actions) -> str:
    metric_bits = [
        f"{metric.label} is {metric.display_value}"
        for metric in overview.metrics[:3]
        if metric.value is not None
    ]
    if metric_bits:
        lead = "; ".join(metric_bits) + "."
    else:
        lead = "The current dataset has no validated headline metrics in this scope."
    if insights.insights:
        lead += f" {len(insights.insights)} evidence-backed signal(s) merit review."
    elif actions.actions:
        lead += f" {len(actions.actions)} evidence-backed action(s) are available."
    else:
        lead += " No validated risk or opportunity threshold is active."
    return lead


def build_report(dataset_id: str, scope=None) -> ReportResponse:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")

    overview = build_overview(dataset_id, scope=scope)
    insights = build_insights(dataset_id, scope=scope)
    actions = build_actions(dataset_id, scope=scope)

    current_scope = scope_label(scope) if scope is not None else "All data"
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return ReportResponse(
        dataset_id=dataset_id,
        file_name=summary.file_name,
        business_model=summary.business_model,
        business_model_label=summary.business_model_label,
        scope_label=current_scope,
        title=f"Executive report — {summary.business_model_label or 'Business performance'}",
        executive_summary=_summary_text(overview, insights, actions),
        generated_at=generated_at,
        metrics=overview.metrics,
        what_changed=overview.what_changed,
        attention=overview.attention,
        opportunities=overview.opportunities,
        actions=actions.actions,
        source_note="Generated from the validated dataset, current analytical scope, and the same evidence-backed services used by Overview, Insights, and Actions.",
    )
