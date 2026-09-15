from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal

from ..contracts import OverviewResponse


PlanIntent = Literal["metric", "ranking", "change", "causal", "unsupported"]

_METRIC_ALIASES = {
    "transactional_sales": {
        "average order value": "aov", "return rate": "return_rate", "average discount": "average_discount", "discount": "average_discount",
        "order count": "orders", "orders": "orders", "quantity": "quantity", "units": "quantity", "revenue": "revenue", "sales": "revenue", "turnover": "revenue",
    },
    "sales_pipeline": {
        "weighted pipeline": "weighted_forecast", "weighted forecast": "weighted_forecast", "pipeline value": "pipeline_value", "pipeline": "pipeline_value",
        "forecast": "weighted_forecast", "opportunities": "opportunities", "deals": "opportunities", "win rate": "win_rate", "conversion rate": "win_rate",
    },
    "subscription": {
        "monthly recurring revenue": "mrr", "annual recurring revenue": "arr", "churn rate": "churn", "mrr": "mrr", "arr": "arr", "churn": "churn",
    },
    "services": {
        "billing per hour": "billing_per_hour", "revenue per hour": "billing_per_hour", "billings": "billings", "billing": "billings", "hours": "hours",
    },
}

_DIMENSION_ALIASES = {
    "transactional_sales": {"payment method": "payment_method", "product": "product", "customer": "customer", "region": "region", "payment": "payment_method"},
    "sales_pipeline": {"salesperson": "salesperson", "customer": "customer", "account": "customer", "stage": "stage", "rep": "salesperson"},
    "subscription": {"churn status": "churn_status", "customer": "customer", "plan": "plan", "status": "churn_status"},
    "services": {"client": "client", "customer": "client", "service": "service", "employee": "employee", "staff": "employee"},
}

_RANK_WORDS = {"highest", "lowest", "top", "best", "worst", "most", "least"}
_CHANGE_WORDS = {"changed", "change", "movement", "moved", "versus", "compared"}
_CAUSAL_WORDS = {"why", "cause", "caused"}


@dataclass(frozen=True)
class AnalyticalPlan:
    """Small, inspectable instructions for deterministic Ask execution."""

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
    return metric if any(item.id == metric for item in overview.metrics) else None


def _validated_dimension(dimension: str | None, validated_dimensions: Iterable[str] | None) -> str | None:
    if dimension is None:
        return None
    if validated_dimensions is None:
        return dimension
    valid = set(validated_dimensions)
    return dimension if dimension in valid else None


def build_plan(
    question: str,
    primary: str | None,
    overview: OverviewResponse,
    validated_dimensions: Iterable[str] | None = None,
) -> AnalyticalPlan:
    """Translate a question into a deterministic analytical execution plan."""
    q = _canon(question)
    if not q:
        return AnalyticalPlan(intent="unsupported", supported=False, reason="Question is empty.")

    primary_key = primary or ""
    metric = _validated_metric(_pick_alias(q, _METRIC_ALIASES.get(primary_key, {})), overview)
    dimension = _validated_dimension(_pick_alias(q, _DIMENSION_ALIASES.get(primary_key, {})), validated_dimensions)
    evidence_requested = any(term in q for term in ("evidence", "calculation", "source fields"))

    if any(token in q.split() for token in _CAUSAL_WORDS):
        return AnalyticalPlan(
            intent="causal", metric=metric, dimension=dimension, evidence_requested=evidence_requested,
            reason="Use validated Insights evidence objects for a causal question.",
        )

    if any(token in q.split() for token in _CHANGE_WORDS):
        if metric is None:
            metric = next((item.id for item in overview.metrics if item.delta_pct is not None), None)
        supported = metric is not None and any(item.id == metric and item.delta_pct is not None for item in overview.metrics)
        return AnalyticalPlan(
            intent="change", metric=metric, dimension=dimension, evidence_requested=evidence_requested,
            supported=supported,
            reason=("Change questions use the validated period-over-period movement on Overview metrics." if supported else "No validated comparison movement is available for the requested question."),
        )

    if any(re.search(rf"\b{re.escape(word)}\b", q) for word in _RANK_WORDS):
        if metric is None:
            metric = next((item.id for item in overview.metrics if item.id != "arr"), None)
        direction = "lowest" if any(word in q.split() for word in ("lowest", "least", "worst")) else "highest"
        if dimension is None:
            return AnalyticalPlan(
                intent="ranking", metric=metric, direction=direction, evidence_requested=evidence_requested, supported=False,
                reason="A ranking requires a validated dimension present in the dataset, such as product, stage, customer, or salesperson.",
            )
        return AnalyticalPlan(
            intent="ranking", metric=metric, dimension=dimension, direction=direction,
            evidence_requested=evidence_requested, supported=metric is not None,
            reason="Ranking is executed through the deterministic Explore aggregation.",
        )

    if metric is not None:
        return AnalyticalPlan(
            intent="metric", metric=metric, dimension=dimension, evidence_requested=evidence_requested,
            reason="Question maps to a validated metric exposed by the current Overview contract.",
        )

    return AnalyticalPlan(
        intent="unsupported", dimension=dimension, evidence_requested=evidence_requested, supported=False,
        reason="The question did not map to a validated metric or supported analysis for this dataset.",
    )
