from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .contracts import (HealthResponse, OnboardingResponse, OverviewResponse, ExploreResponse, InsightsResponse, AskResponse, ActionsResponse, ReportResponse, AnalysisSession, ScopeFilter, ScopeState, ScopeValuesResponse, ScopeValue, AlertsResponse, AlertRule, AlertRuleCreate)
from .services.onboarding import get_dataset, onboard
from .services.overview import build_overview
from .services.explore import build_explore
from .services.insights import build_insights
from .services.ask import answer_question
from .services.actions import build_actions
from .services.report import build_report
from .services.session import create_session, get_session, replace_dataset, update_scope, reset_scope
from .services.monitoring import list_alerts, create_rule, delete_rule, evaluate_alerts

app = FastAPI(title="AI Sales Analyst API", version="4.0.0-alpha.1", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])


def _scope_for(dataset_id: str, session_id: str | None):
    if not session_id:
        return None
    current = get_session(session_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    if current.dataset_id != dataset_id:
        raise HTTPException(status_code=409, detail="Analysis session does not match the dataset.")
    return current.scope

@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", product="AI Sales Analyst", version="4.0.0-alpha.1")

@app.post("/api/v1/onboarding/profile", response_model=OnboardingResponse)
async def profile_upload(file: UploadFile = File(...)) -> OnboardingResponse:
    try:
        summary = onboard(file.filename or "upload", file.file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not understand this file: {exc}") from exc
    session = create_session(summary.dataset_id)
    return OnboardingResponse(dataset=summary, message="Your dataset is ready for analysis.", session_id=session.session_id)

@app.get("/api/v1/datasets/{dataset_id}")
def dataset(dataset_id: str):
    summary = get_dataset(dataset_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return summary

@app.get("/api/v1/datasets/{dataset_id}/overview", response_model=OverviewResponse)
def overview(dataset_id: str, session_id: str | None = None) -> OverviewResponse:
    try:
        return build_overview(dataset_id, scope=_scope_for(dataset_id, session_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build overview: {exc}") from exc


@app.get("/api/v1/datasets/{dataset_id}/explore", response_model=ExploreResponse)
def explore(dataset_id: str, metric: str | None = None, dimension: str | None = None, limit: int = 8, session_id: str | None = None) -> ExploreResponse:
    try:
        return build_explore(dataset_id, metric, dimension, limit, scope=_scope_for(dataset_id, session_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build exploration: {exc}") from exc


@app.get("/api/v1/datasets/{dataset_id}/insights", response_model=InsightsResponse)
def insights(dataset_id: str, session_id: str | None = None) -> InsightsResponse:
    try:
        return build_insights(dataset_id, scope=_scope_for(dataset_id, session_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build insights: {exc}") from exc


@app.post("/api/v1/datasets/{dataset_id}/ask", response_model=AskResponse)
def ask(dataset_id: str, question: str, session_id: str | None = None) -> AskResponse:
    try:
        return answer_question(dataset_id, question, scope=_scope_for(dataset_id, session_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not answer the question: {exc}") from exc


@app.get("/api/v1/datasets/{dataset_id}/actions", response_model=ActionsResponse)
def actions(dataset_id: str, session_id: str | None = None) -> ActionsResponse:
    try:
        return build_actions(dataset_id, scope=_scope_for(dataset_id, session_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build actions: {exc}") from exc




@app.get("/api/v1/datasets/{dataset_id}/report", response_model=ReportResponse)
def report(dataset_id: str, session_id: str | None = None) -> ReportResponse:
    try:
        return build_report(dataset_id, scope=_scope_for(dataset_id, session_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build report: {exc}") from exc


@app.get("/api/v1/datasets/{dataset_id}/alerts", response_model=AlertsResponse)
def alerts(dataset_id: str, session_id: str | None = None) -> AlertsResponse:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for monitoring.")
    try:
        return list_alerts(dataset_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/datasets/{dataset_id}/alerts", response_model=AlertRule)
def create_alert(dataset_id: str, request: AlertRuleCreate, session_id: str | None = None) -> AlertRule:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for monitoring.")
    try:
        return create_rule(dataset_id, session_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/v1/datasets/{dataset_id}/alerts/{rule_id}")
def remove_alert(dataset_id: str, rule_id: str, session_id: str | None = None):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for monitoring.")
    try:
        delete_rule(dataset_id, session_id, rule_id)
        return {"status": "ok"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/datasets/{dataset_id}/alerts/evaluate", response_model=AlertsResponse)
def evaluate_dataset_alerts(dataset_id: str, session_id: str | None = None) -> AlertsResponse:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for monitoring.")
    try:
        return evaluate_alerts(dataset_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/sessions", response_model=AnalysisSession)
def create_session_endpoint(body: dict) -> AnalysisSession:
    dataset_id = str(body.get("dataset_id") or "").strip()
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required.")
    try:
        return create_session(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@app.get("/api/v1/sessions/{session_id}", response_model=AnalysisSession)
def session(session_id: str) -> AnalysisSession:
    value = get_session(session_id)
    if value is None:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    return value


@app.post("/api/v1/sessions/{session_id}/dataset/{dataset_id}", response_model=AnalysisSession)
def session_dataset(session_id: str, dataset_id: str) -> AnalysisSession:
    try:
        return replace_dataset(session_id, dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class ScopeUpdate(AnalysisSession):
    pass


@app.post("/api/v1/sessions/{session_id}/scope", response_model=AnalysisSession)
def session_scope(session_id: str, body: dict) -> AnalysisSession:
    try:
        filters = [ScopeFilter.model_validate(item) for item in body.get("filters", [])]
        return update_scope(session_id, filters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc




@app.get("/api/v1/sessions/{session_id}/scope-values", response_model=ScopeValuesResponse)
def session_scope_values(session_id: str, field: str, limit: int = 100) -> ScopeValuesResponse:
    from .services.session import scope_values
    try:
        values = scope_values(session_id, field, limit)
        return ScopeValuesResponse(field=field, values=[ScopeValue(value=v, label=v) for v in values])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/api/v1/sessions/{session_id}/scope/reset", response_model=AnalysisSession)
def session_scope_reset(session_id: str) -> AnalysisSession:
    try:
        return reset_scope(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
