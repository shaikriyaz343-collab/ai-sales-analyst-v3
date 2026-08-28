from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from schema_profiler_v2 import load_dataframe, profile_dataframe
from semantic_business_model_v2 import build_semantic_model
from business_type_detector_v1 import detect_business_type

from ..contracts import AskAnswer, AskEvidence, AskResponse, AskFollowUp
from .onboarding import STORAGE, get_dataset
from .overview import build_overview
from .explore import build_explore
from .insights import build_insights


def _canon(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def _label_metric(metric: str) -> str:
    return {
        "revenue": "revenue", "orders": "orders", "quantity": "units sold", "aov": "average order value",
        "return_rate": "return rate", "average_discount": "average discount",
        "pipeline_value": "pipeline", "weighted_forecast": "weighted forecast", "weighted_pipeline": "weighted pipeline",
        "opportunities": "opportunities", "win_rate": "win rate", "mrr": "MRR", "arr": "ARR", "churn": "churn",
        "churn_rate": "churn rate", "billings": "billings", "hours": "hours", "billing_per_hour": "billing per hour",
    }.get(metric, metric.replace("_", " "))


def _metric_aliases(primary: str) -> dict[str, str]:
    common = {
        "revenue": "revenue", "sales": "revenue", "turnover": "revenue",
        "orders": "orders", "order count": "orders", "quantity": "quantity", "units": "quantity",
        "aov": "aov", "average order value": "aov", "average order": "aov", "return rate": "return_rate", "returns": "return_rate",
    }
    return {
        "transactional_sales": {**common, "discount": "average_discount", "average discount": "average_discount"},
        "sales_pipeline": {
            "pipeline": "pipeline_value", "pipeline value": "pipeline_value", "weighted pipeline": "weighted_forecast",
            "weighted forecast": "weighted_forecast", "forecast": "weighted_forecast", "opportunities": "opportunities", "deals": "opportunities",
            "win rate": "win_rate", "conversion rate": "win_rate",
        },
        "subscription": {"mrr": "mrr", "monthly recurring revenue": "mrr", "arr": "arr", "annual recurring revenue": "arr", "churn": "churn", "churn rate": "churn"},
        "services": {"billings": "billings", "billing": "billings", "hours": "hours", "billing per hour": "billing_per_hour", "revenue per hour": "billing_per_hour"},
    }.get(primary, {})


def _dimension_aliases(primary: str) -> dict[str, str]:
    return {
        "transactional_sales": {"product": "product", "customer": "customer", "region": "region", "payment": "payment_method", "payment method": "payment_method"},
        "sales_pipeline": {"stage": "stage", "salesperson": "salesperson", "rep": "salesperson", "account": "customer", "customer": "customer"},
        "subscription": {"customer": "customer", "plan": "plan", "churn status": "churn_status", "status": "churn_status"},
        "services": {"client": "client", "customer": "client", "service": "service", "employee": "employee", "staff": "employee"},
    }.get(primary, {})


def _supported_text(summary) -> str:
    analytics = summary.capabilities.analytics
    if not analytics:
        return "No validated analytical metrics are currently available for this dataset."
    labels = [_label_metric(x) for x in analytics]
    return "Available validated metrics include " + ", ".join(labels[:8]) + "."


def _pick_metric(question: str, primary: str, overview) -> str | None:
    q = _canon(question)
    aliases = _metric_aliases(primary)
    # Prefer longer phrases first.
    for alias in sorted(aliases, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", q):
            metric = aliases[alias]
            if any(m.id == metric for m in overview.metrics):
                return metric
            if primary == "subscription" and metric == "arr" and any(m.id == "arr" for m in overview.metrics):
                return "arr"
            if primary == "services" and metric == "billing_per_hour" and any(m.id == "billing_per_hour" for m in overview.metrics):
                return metric
    return None


def _pick_dimension(question: str, primary: str) -> str | None:
    q = _canon(question)
    aliases = _dimension_aliases(primary)
    for alias in sorted(aliases, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", q):
            return aliases[alias]
    return None


def _is_rank(question: str) -> bool:
    q = _canon(question)
    return any(re.search(rf"\b{w}\b", q) for w in ("highest", "lowest", "top", "best", "worst", "most", "least"))


def _ranking_direction(question: str) -> str:
    q = _canon(question)
    return "lowest" if any(w in q for w in ("lowest", "least", "worst")) else "highest"


def _answer_from_overview(summary, overview, question: str, metric_id: str) -> tuple[AskAnswer, list[AskFollowUp]]:
    metric = next((m for m in overview.metrics if m.id == metric_id), None)
    if metric is None or metric.value is None:
        answer = AskAnswer(
            status="unsupported",
            text=f"I can't calculate {_label_metric(metric_id)} from the validated fields in this dataset without guessing.",
            confidence="high",
            evidence=None,
        )
        return answer, [AskFollowUp(label="What can you calculate?", question="What metrics are available?")]
    evidence = AskEvidence(**metric.evidence.model_dump())
    text = f"{metric.label} is {metric.display_value}."
    if metric.delta_label and metric.delta_pct is not None:
        direction = "increased" if metric.delta_pct >= 0 else "decreased"
        text += f" It {direction} {abs(metric.delta_pct):.1f}% versus {metric.delta_label}."
    answer = AskAnswer(status="answered", text=text, confidence="high", evidence=evidence)
    dim = next((d for d in (summary.semantic.dimensions if summary.semantic else []) if d not in {"date"}), None)
    followups = [AskFollowUp(label=f"Show {metric.label.lower()} by {dim.replace('_',' ') if dim else 'dimension'}", question=f"Show me {_label_metric(metric_id)} by {dim.replace('_',' ') if dim else 'dimension'}."), AskFollowUp(label="Show the calculation", question="Show the calculation and evidence.")]
    return answer, followups


def answer_question(dataset_id: str, question: str, scope=None) -> AskResponse:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")
    question = (question or "").strip()
    if not question:
        return AskResponse(dataset_id=dataset_id, question="", business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="needs_question", text="Enter a question about this dataset.", confidence="high"), follow_ups=[])

    suffix = Path(summary.file_name).suffix.lower()
    path = STORAGE / f"{dataset_id}{suffix}"
    if not path.exists():
        raise ValueError("Dataset file is no longer available for analysis.")

    data = load_dataframe(path)
    profile = profile_dataframe(path)
    semantic = build_semantic_model(profile, data=data)
    business = detect_business_type(semantic, profile)
    primary = business.get("primary_type") or summary.business_model
    overview = build_overview(dataset_id, scope=scope)

    # "why/change" questions are grounded in the same Insight objects used by Insights.
    q = _canon(question)
    if any(term in q.split() for term in ("why", "cause", "caused", "changed", "change")):
        insights = build_insights(dataset_id, scope=scope)
        if insights.insights:
            target_metric = _pick_metric(question, primary, overview)
            selected = next((i for i in insights.insights if target_metric and i.metric == target_metric), insights.insights[0])
            evidence = AskEvidence(**selected.evidence.model_dump())
            text = f"{selected.title}. {selected.why_it_matters} {selected.recommendation}"
            followups = [
                AskFollowUp(label="Explore the driver", question=f"Show {_label_metric(selected.metric)} by customer." if primary != "sales_pipeline" else "Show weighted pipeline by stage."),
                AskFollowUp(label="Show evidence", question="Show the calculation and source fields."),
            ]
            return AskResponse(dataset_id=dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="answered", text=text, confidence="high", evidence=evidence), follow_ups=followups)
        return AskResponse(dataset_id=dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="unsupported", text="I don't have a validated causal finding for that question in this dataset. I won't invent a reason.", confidence="high"), follow_ups=[AskFollowUp(label="Explore the data", question="What metrics are available?")])

    metric_id = _pick_metric(question, primary, overview)
    dimension = _pick_dimension(question, primary)
    if _is_rank(question):
        if dimension is None:
            # Infer a ranking entity from wording.
            for key in _dimension_aliases(primary):
                if key in q:
                    dimension = _dimension_aliases(primary)[key]
                    break
        if metric_id is None:
            metric_id = next((m.id for m in overview.metrics if m.id not in {"arr"}), overview.metrics[0].id if overview.metrics else None)
        if metric_id and dimension:
            try:
                result = build_explore(dataset_id, metric_id, dimension, 1, scope=scope)
            except ValueError as exc:
                return AskResponse(dataset_id=dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="unsupported", text=str(exc), confidence="high"), follow_ups=[])
            if not result.rows:
                return AskResponse(dataset_id=dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="no_data", text="I couldn't find a matching result in the current dataset.", confidence="high"), follow_ups=[])
            row = result.rows[0] if _ranking_direction(question) == "highest" else build_explore(dataset_id, metric_id, dimension, 15, scope=scope).rows[-1]
            direction = "highest" if _ranking_direction(question) == "highest" else "lowest"
            text = f"The {dimension.replace('_',' ')} with the {direction} {_label_metric(metric_id)} is {row.key} at {row.display_value}."
            evidence = AskEvidence(**row.evidence)
            followups = [AskFollowUp(label="Explore this", question=f"Show {_label_metric(metric_id)} by {dimension.replace('_',' ')}."), AskFollowUp(label="Show evidence", question="Show the calculation and source fields.")]
            return AskResponse(dataset_id=dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="answered", text=text, confidence="high", evidence=evidence), follow_ups=followups, explore_metric=metric_id, explore_dimension=dimension)

    if metric_id:
        answer, followups = _answer_from_overview(summary, overview, question, metric_id)
        return AskResponse(dataset_id=dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=answer, follow_ups=followups, explore_metric=metric_id, explore_dimension=dimension)

    return AskResponse(
        dataset_id=dataset_id,
        question=question,
        business_model=summary.business_model,
        business_model_label=summary.business_model_label,
        answer=AskAnswer(status="unsupported", text="I couldn't map that question to a validated metric or analysis for this dataset. I won't guess.", confidence="high"),
        follow_ups=[AskFollowUp(label="See available metrics", question="What metrics are available?"), AskFollowUp(label="Open Explore", question="Show me the available analyses.")],
        supported_summary=_supported_text(summary),
    )
