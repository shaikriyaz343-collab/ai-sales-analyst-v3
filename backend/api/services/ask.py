from __future__ import annotations

from pathlib import Path

from business_type_detector_v1 import detect_business_type
from schema_profiler_v2 import load_dataframe, profile_dataframe
from semantic_business_model_v2 import build_semantic_model

from ..contracts import AskAnswer, AskEvidence, AskResponse, AskFollowUp
from .ask_planner import AnalyticalPlan, build_plan
from .onboarding import STORAGE, get_dataset
from .overview import build_overview
from .explore import build_explore
from .insights import build_insights


def _label_metric(metric: str) -> str:
    return {
        "revenue": "revenue", "orders": "orders", "quantity": "units sold", "aov": "average order value", "return_rate": "return rate", "average_discount": "average discount",
        "pipeline_value": "pipeline", "weighted_forecast": "weighted forecast", "weighted_pipeline": "weighted pipeline", "opportunities": "opportunities", "win_rate": "win rate",
        "mrr": "MRR", "arr": "ARR", "churn": "churn", "churn_rate": "churn rate", "billings": "billings", "hours": "hours", "billing_per_hour": "billing per hour",
    }.get(metric, metric.replace("_", " "))


def _supported_text(summary) -> str:
    analytics = summary.capabilities.analytics
    if not analytics:
        return "No validated analytical metrics are currently available for this dataset."
    labels = [_label_metric(x) for x in analytics]
    return "Available validated metrics include " + ", ".join(labels[:8]) + "."


def _with_plan(response: AskResponse, plan: AnalyticalPlan) -> AskResponse:
    response.analytical_plan = plan.as_dict()
    return response


def _answer_from_overview(summary, overview, metric_id: str) -> tuple[AskAnswer, list[AskFollowUp]]:
    metric = next((m for m in overview.metrics if m.id == metric_id), None)
    if metric is None or metric.value is None:
        return AskAnswer(status="unsupported", text=f"I can't calculate {_label_metric(metric_id)} from the validated fields in this dataset without guessing.", confidence="high"), [AskFollowUp(label="What do you have?", question="What metrics are available?")]
    evidence = AskEvidence(**metric.evidence.model_dump())
    text = f"{metric.label} is {metric.display_value}."
    if metric.delta_label and metric.delta_pct is not None:
        direction = "increased" if metric.delta_pct >= 0 else "decreased"
        text += f" It {direction} {abs(metric.delta_pct):.1f}% versus {metric.delta_label}."
    dim = next((d for d in (summary.semantic.dimensions if summary.semantic else []) if d != "date"), None)
    followups = [
        AskFollowUp(label=f"Show {metric.label.lower()} by {dim.replace('_', ' ') if dim else 'dimension'}", question=f"Show me {_label_metric(metric_id)} by {dim.replace('_', ' ') if dim else 'dimension'}."),
        AskFollowUp(label="Show the calculation", question="Show the calculation and evidence."),
    ]
    return AskAnswer(status="answered", text=text, confidence="high", evidence=evidence), followups


def _answer_change(summary, overview, question: str, plan: AnalyticalPlan) -> AskResponse:
    metric = next((m for m in overview.metrics if m.id == plan.metric), None) if plan.metric else next((m for m in overview.metrics if m.delta_pct is not None), None)
    if metric is None or metric.delta_pct is None:
        return AskResponse(
            dataset_id=summary.dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label,
            answer=AskAnswer(status="unsupported", text=plan.reason, confidence="high"), follow_ups=[AskFollowUp(label="See available metrics", question="What metrics are available?")],
        )
    direction = "increased" if metric.delta_pct >= 0 else "decreased"
    text = f"{metric.label} {direction} {abs(metric.delta_pct):.1f}% versus {metric.delta_label or 'the validated comparison period'}."
    followups = [
        AskFollowUp(label="Show the calculation", question="Show the calculation and evidence."),
        AskFollowUp(label="Explore the driver", question=f"Show {_label_metric(metric.id)} by customer."),
    ]
    return AskResponse(
        dataset_id=summary.dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label,
        answer=AskAnswer(status="answered", text=text, confidence="high", evidence=AskEvidence(**metric.evidence.model_dump())), follow_ups=followups,
        explore_metric=metric.id,
    )


def _answer_causal(summary, question: str, scope, plan: AnalyticalPlan) -> AskResponse:
    insights = build_insights(summary.dataset_id, scope=scope)
    if insights.insights:
        selected = next((i for i in insights.insights if plan.metric and i.metric == plan.metric), insights.insights[0])
        evidence = AskEvidence(**selected.evidence.model_dump())
        text = f"{selected.title}. {selected.why_it_matters} {selected.recommendation}"
        followups = [AskFollowUp(label="Explore the driver", question=(f"Show {_label_metric(selected.metric)} by stage." if summary.business_model == "sales_pipeline" else f"Show {_label_metric(selected.metric)} by customer.")), AskFollowUp(label="Show evidence", question="Show the calculation and source fields.")]
        return AskResponse(dataset_id=summary.dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="answered", text=text, confidence="high", evidence=evidence), follow_ups=followups)
    return AskResponse(dataset_id=summary.dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="unsupported", text="I don't have a validated causal finding for that question in this dataset. I won't invent a reason.", confidence="high"), follow_ups=[AskFollowUp(label="Explore the data", question="What metrics are available?")])


def _execute_ranking(summary, question: str, scope, plan: AnalyticalPlan) -> AskResponse:
    if not plan.supported or not plan.metric or not plan.dimension:
        return AskResponse(dataset_id=summary.dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="unsupported", text=plan.reason, confidence="high"), follow_ups=[AskFollowUp(label="See available metrics", question="What metrics are available?")], supported_summary=_supported_text(summary))
    try:
        result = build_explore(summary.dataset_id, plan.metric, plan.dimension, 15, scope=scope)
    except ValueError as exc:
        return AskResponse(dataset_id=summary.dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="unsupported", text=str(exc), confidence="high"), follow_ups=[])
    if not result.rows:
        return AskResponse(dataset_id=summary.dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="no_data", text="I couldn't find a matching result in the current dataset.", confidence="high"), follow_ups=[])
    row = result.rows[0] if plan.direction == "highest" else result.rows[-1]
    text = f"The {plan.dimension.replace('_', ' ')} with the {plan.direction or 'highest'} {_label_metric(plan.metric)} is {row.key} at {row.display_value}."
    evidence = AskEvidence(**row.evidence)
    return AskResponse(dataset_id=summary.dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="answered", text=text, confidence="high", evidence=evidence), follow_ups=[AskFollowUp(label="Explore this", question=f"Show {_label_metric(plan.metric)} by {plan.dimension.replace('_', ' ')}."), AskFollowUp(label="Show evidence", question="Show the calculation and source fields.")], explore_metric=plan.metric, explore_dimension=plan.dimension)


def answer_question(dataset_id: str, question: str, scope=None) -> AskResponse:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")
    question = (question or "").strip()
    if not question:
        plan = AnalyticalPlan(intent="unsupported", supported=False, reason="Question is empty.")
        return _with_plan(AskResponse(dataset_id=dataset_id, question="", business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="needs_question", text="Enter a question about this dataset.", confidence="high"), follow_ups=[]), plan)

    primary = summary.business_model
    if not primary:
        suffix = Path(summary.file_name).suffix.lower()
        path = STORAGE / f"{dataset_id}{suffix}"
        if not path.exists():
            raise ValueError("Dataset file is no longer available for analysis.")
        data = load_dataframe(path)
        profile = profile_dataframe(data)
        semantic = build_semantic_model(profile, data=data)
        primary = detect_business_type(semantic, profile).get("primary_type")

    overview = build_overview(dataset_id, scope=scope)
    validated_dimensions = summary.semantic.dimensions if summary.semantic else None
    plan = build_plan(question, primary, overview, validated_dimensions=validated_dimensions)

    if plan.intent == "change":
        return _with_plan(_answer_change(summary, overview, question, plan), plan)
    if plan.intent == "causal":
        return _with_plan(_answer_causal(summary, question, scope, plan), plan)
    if plan.intent == "ranking":
        return _with_plan(_execute_ranking(summary, question, scope, plan), plan)
    if plan.intent == "metric" and plan.metric:
        answer, followups = _answer_from_overview(summary, overview, plan.metric)
        return _with_plan(AskResponse(dataset_id=dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=answer, follow_ups=followups, explore_metric=plan.metric, explore_dimension=plan.dimension), plan)

    return _with_plan(AskResponse(dataset_id=dataset_id, question=question, business_model=summary.business_model, business_model_label=summary.business_model_label, answer=AskAnswer(status="unsupported", text="I couldn't map that question to a validated metric or analysis for this dataset. I won't guess.", confidence="high"), follow_ups=[AskFollowUp(label="See available metrics", question="What metrics are available?"), AskFollowUp(label="Open Explore", question="Show me the available analyses.")], supported_summary=_supported_text(summary)), plan)
