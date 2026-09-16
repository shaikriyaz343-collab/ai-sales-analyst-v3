from __future__ import annotations

from dataclasses import dataclass

from ..contracts import ActionItem, ActionsResponse
from .onboarding import get_dataset
from .overview import build_overview


@dataclass(frozen=True)
class _ActionContext:
    owner: str
    prefix: str


_OWNER_BY_MODEL = {
    "transactional_sales": _ActionContext("Sales / Operations", "Commercial action"),
    "sales_pipeline": _ActionContext("Sales Leadership", "Pipeline action"),
    "subscription": _ActionContext("Customer Success", "Retention action"),
    "services": _ActionContext("Services Leadership", "Delivery action"),
}


def _priority(severity: str) -> str:
    return {"high": "high", "medium": "medium", "info": "normal"}.get(severity, "normal")


def _action_from_insight(insight, context: _ActionContext, status: str = "open") -> ActionItem:
    return ActionItem(
        id=f"action-{insight.id}",
        priority=_priority(insight.severity),
        status=status,
        title=insight.title,
        action=insight.recommendation,
        owner=context.owner,
        rationale=insight.why_it_matters,
        expected_outcome="Use the validated evidence to address the identified business signal before changing plans.",
        metric=insight.evidence.metric,
        display_value=(
            f"{insight.evidence.value:.1f}%"
            if insight.evidence.value is not None and insight.evidence.metric in {
                "return_rate", "churn", "win_rate", "customer_revenue_share",
                "weighted_pipeline_share", "product_revenue_share",
            }
            else (f"${insight.evidence.value:,.0f}" if insight.evidence.value is not None else "—")
        ),
        evidence=insight.evidence,
        source_insight_id=insight.id,
    )


def build_actions(dataset_id: str, scope=None, session_id: str | None = None) -> ActionsResponse:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")

    context = _OWNER_BY_MODEL.get(summary.business_model or "", _ActionContext("Business owner", "Business action"))
    overview = build_overview(dataset_id, scope=scope)

    status_lookup = None
    if session_id:
        from .action_workflow import status_for
        status_lookup = lambda action_id: status_for(session_id, action_id)

    source_insights = [*overview.attention, *overview.opportunities]
    actions = [
        _action_from_insight(item, context, status=status_lookup(f"action-{item.id}") if status_lookup else "open")
        for item in source_insights
    ]

    # Deterministic ordering: risk first, then opportunity, then severity.
    priority_rank = {"high": 0, "medium": 1, "normal": 2}
    actions.sort(key=lambda a: (priority_rank.get(a.priority, 3), a.title.lower()))

    return ActionsResponse(
        dataset_id=summary.dataset_id,
        business_model=summary.business_model,
        business_model_label=summary.business_model_label,
        headline="Turn insight into action",
        summary="Prioritized actions derived only from validated risks and opportunities in the current dataset. Status is user-controlled when a session is active.",
        actions=actions[:8],
    )
