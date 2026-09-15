from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from ..contracts import OverviewResponse


PlanIntent = Literal["metric", "ranking", "causal", "unsupported"]

_METRIC_ALIASES = {
    "transactional_sales": {
        "average order value": "aov",
        "return rate": "return_rate",
        "average discount": "average_discount",
        "discount": "average_discount",
        "order count": "orders",
        "orders": "orders",
        "quantity": "quantity",
        "units": "quantity",
        "revenue": "revenue",
        "sales": "revenue",
        "turnover": "revenue",
    },
    "sales_pipeline": {
        "weighted pipeline": "weighted_forecast",
        "weighted forecast": "weighted_forecast",
        "pipeline value": "pipeline_value",
        "pipeline": "pipeline_value",
        "forecast": "weighted_forecast",
        "opportunities": "opportunities",
        "deals": "opportunities",
        "win rate": "win_rate",
        "conversion rate": "win_rate",
    },
    "subscription": {
        "monthly recurring revenue": "mrr",
        "annual recurring revenue": "arr",
        "churn rate": "churn",
        "mrr": "mrr",
        "arr": "arr",
        "churn": "churn",
    },
    "services": {
        "billing per hour": "billing_per_hour",
        "revenue per hour": "billing_per_hour",
        "billings": "billings",
        "billing": "billings",
        "hours": "hours",
    },
}

_DIMENSION_ALIASES = {
    "transactional_sales": {
        "payment method": "payment_method",
        "product": "product",
        "customer": "customer",
        "region": "region",
        "payment": "payment_method",
    },
    "sales_pipeline": {
        "salesperson": "salesperson",
        "customer": "customer",
        "account": "customer",
        "stage": "stage",
        "rep": "salesperson",
    },
    "subscription": {
        "churn status": "churn_status",
        "customer": "customer",
        "plan": "plan",
        "status": "churn_status",
    },
    "services": {
        "client": "client",
        "customer": "client",
        "service": "service",
        "employee": "employee",
        "staff": "employee",
    },
}

_RANK_WORDS = {"highest", "lowest", "top", "best", "worst", "most", "least"}
_CAUSAL_WORDS = {"why", "cause", "caused", "changed", "change"}


@dataclass(frozen=True)
class AnalyticalPlan:
    """A small, inspectable plan that tells Ask what deterministic work to run."""

    intent: PlanIntent
    metric: str | None = None
    dimension: str | None = None
    direction: str | None = None
    evidence_requested: bool = False
    supported: bool = True
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "metric": self.metric,
            "dimension": self.dimension,
            "direction": self.direction,
            "evidence_requested": self.evidence_requested,
            "supported": self.supported,
            "reason": self.reason,
        }


def _canon(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def _pick_alias(question: str, aliases: dict[str, str]) -> str | None:
    for alias in sorted(aliases, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", question):
            return aliases[alias]
    return None


def _validated_metric(metric: str | None, overview: OverviewResponse) -> str | None:
    if metric is None:
        return None
    if any(item.id == metric for item in overview.metrics):
        return metric
    return None


def build_plan(question: str, primary: str | None, overview: OverviewResponse) -> AnalyticalPlan:
    """Translate a user question into a deterministic analytical execution plan.

    Planning never calculates a business value. It only selects an intent and
    validated metric/dimension targets; execution remains inside the existing
    Overview/Explore/Insights engines.
    """
    q = _canon(question)
    if not q:
        return AnalyticalPlan(intent="unsupported", supported=False, reason="Question is empty.")

    primary_key = primary or ""
    metric_aliases = _METRIC_ALIASES.get(primary_key, {})
    dimension_aliases = _DIMENSION_ALIASES.get(primary_key, {})
    metric = _validated_metric(_pick_alias(q, metric_aliases), overview)
    dimension = _pick_alias(q, dimension_aliases)
    evidence_requested = "evidence" in q or "calculation" in q or "source fields" in q

    if any(token in q.split() for token in _CAUSAL_WORDS):
        return AnalyticalPlan(
            intent="causal",
            metric=metric,
            dimension=dimension,
            evidence_requested=evidence_requested,
            reason="Question asks for a validated reason or period movement, so execution should use the existing Insights evidence objects.",
        )

    if any(re.search(rf"\b{re.escape(word)}\b", q) for word in _RANK_WORDS):
        if metric is None:
            metric = next((item.id for item in overview.metrics if item.id != "arr"), None)
        direction = "lowest" if any(word in q.split() for word in ("lowest", "least", "worst")) else "highest"
        if dimension is None:
            return AnalyticalPlan(
                intent="ranking",
                metric=metric,
                direction=direction,
                evidence_requested=evidence_requested,
                supported=False,
                reason="A ranking requires a validated dimension such as product, stage, customer, or salesperson.",
            )
        return AnalyticalPlan(
            intent="ranking",
            metric=metric,
            dimension=dimension,
            direction=direction,
            evidence_requested=evidence_requested,
            supported=metric is not None,
            reason="Ranking is executed through the deterministic Explore aggregation.",
        )

    if metric is not None:
        return AnalyticalPlan(
            intent="metric",
            metric=metric,
            dimension=dimension,
            evidence_requested=evidence_requested,
            reason="Question maps to a validated metric exposed by the current Overview contract.",
        )

    return AnalyticalPlan(
        intent="unsupported",
        dimension=dimension,
        evidence_requested=evidence_requested,
        supported=False,
        reason="The question did not map to a validated metric or supported analysis for this dataset.",
    )
