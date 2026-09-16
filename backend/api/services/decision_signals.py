from __future__ import annotations

from dataclasses import dataclass

from ..contracts import Evidence, OverviewInsight, OverviewResponse


_SEVERITY_SCORE = {
    "critical": 100.0,
    "high": 85.0,
    "medium": 65.0,
    "low": 45.0,
    "info": 25.0,
}

_KIND_SCORE = {
    "risk": 90.0,
    "attention": 90.0,
    "opportunity": 60.0,
    "change": 45.0,
}

_MONEY_METRICS = {
    "revenue", "pipeline_value", "weighted_forecast", "mrr", "arr", "billings",
    "aov", "billing_per_hour", "customer_revenue_share", "product_revenue_share",
    "stage_pipeline_value", "customer_mrr", "client_billings",
}


def _display_value(metric: str, value: float | None) -> str:
    if value is None:
        return "—"
    if metric in {"win_rate", "return_rate", "churn", "average_discount", "customer_revenue_share", "weighted_pipeline_share", "product_revenue_share"} or "share" in metric:
        return f"{value:.1f}%"
    if metric == "hours":
        return f"{value:,.0f}"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{sign}${magnitude / 1_000_000:.2f}M"
    if magnitude >= 1_000:
        return f"{sign}${magnitude / 1_000:.1f}K"
    return f"{sign}${magnitude:,.0f}"


@dataclass(frozen=True)
class DecisionSignal:
    """A deterministic, ranked business decision signal.

    Numeric truth comes from the validated Overview/Evidence engine. This
    object only scores and orders those existing signals.
    """

    signal_id: str
    kind: str
    severity: str
    title: str
    summary: str
    why_it_matters: str
    recommendation: str
    metric: str
    value: float | None
    display_value: str
    evidence: Evidence
    impact_score: float
    urgency_score: float
    evidence_score: float
    priority_score: float

    def as_dict(self) -> dict[str, object]:
        return {
            "signal_id": self.signal_id,
            "kind": self.kind,
            "severity": self.severity,
            "title": self.title,
            "summary": self.summary,
            "why_it_matters": self.why_it_matters,
            "recommendation": self.recommendation,
            "metric": self.metric,
            "value": self.value,
            "display_value": self.display_value,
            "evidence": self.evidence.model_dump(),
            "impact_score": self.impact_score,
            "urgency_score": self.urgency_score,
            "evidence_score": self.evidence_score,
            "priority_score": self.priority_score,
        }


def _evidence_score(evidence: Evidence) -> float:
    score = 0.0
    if evidence.metric:
        score += 25.0
    if evidence.calculation:
        score += 25.0
    if evidence.scope:
        score += 15.0
    if evidence.source_fields:
        score += 25.0
    if evidence.value is not None:
        score += 10.0
    return min(100.0, score)


def _urgency_score(kind: str, severity: str) -> float:
    base = _SEVERITY_SCORE.get(severity, 20.0)
    kind_bonus = 10.0 if kind in {"risk", "attention"} else 0.0
    return min(100.0, base + kind_bonus)


def _impact_score(insight: OverviewInsight, kind: str) -> float:
    """Estimate decision impact using validated signal characteristics and kind.

    The caller supplies the signal kind derived from the Overview collection so
    severity cannot accidentally reclassify a high-severity opportunity as a risk.
    Money-like metrics receive a modest boost because they are directly commercial
    measures; non-monetary metrics remain eligible but cannot gain that boost.
    """
    score = _KIND_SCORE.get(kind, 40.0)
    metric = insight.evidence.metric
    if metric in _MONEY_METRICS and insight.evidence.value is not None:
        score += 15.0
    elif insight.evidence.value is not None:
        score += 8.0
    if insight.evidence.source_fields:
        score += 5.0
    return min(100.0, score)


def _signal_from_insight(insight: OverviewInsight, kind: str) -> DecisionSignal:
    evidence = insight.evidence
    evidence_score = _evidence_score(evidence)
    urgency = _urgency_score(kind, insight.severity)
    impact = _impact_score(insight, kind)
    priority = round((impact * 0.40) + (urgency * 0.35) + (evidence_score * 0.25), 2)

    return DecisionSignal(
        signal_id=insight.id,
        kind=kind,
        severity=insight.severity,
        title=insight.title,
        summary=insight.summary,
        why_it_matters=insight.why_it_matters,
        recommendation=insight.recommendation,
        metric=evidence.metric,
        value=evidence.value,
        display_value=_display_value(evidence.metric, evidence.value),
        evidence=evidence,
        impact_score=impact,
        urgency_score=urgency,
        evidence_score=evidence_score,
        priority_score=priority,
    )


def rank_decision_signals(overview: OverviewResponse, *, limit: int = 8) -> list[DecisionSignal]:
    """Rank validated Overview insights into a decision feed."""
    if limit <= 0:
        return []

    signals: list[DecisionSignal] = []
    for insight in overview.attention:
        signals.append(_signal_from_insight(insight, "risk"))
    for insight in overview.opportunities:
        signals.append(_signal_from_insight(insight, "opportunity"))

    signals.sort(
        key=lambda signal: (
            -signal.priority_score,
            -signal.evidence_score,
            signal.signal_id,
        )
    )
    return signals[:limit]
