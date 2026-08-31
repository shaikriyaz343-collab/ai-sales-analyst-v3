from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .config import settings
from .contracts import (
    ActionItem,
    ActionsResponse,
    AlertRule,
    AlertRuleCreate,
    AlertsResponse,
    AnalysisSession,
    AskResponse,
    AuthResponse,
    AuthUser,
    AuthWorkspace,
    CreateWorkspaceRequest,
    ExploreResponse,
    HealthResponse,
    InsightsResponse,
    LoginRequest,
    OnboardingResponse,
    OverviewResponse,
    ReportResponse,
    SavedIntelligence,
    SavedIntelligenceCreate,
    SavedIntelligenceResponse,
    ScopeFilter,
    ScopeValue,
    ScopeValuesResponse,
    SignupRequest,
    WorkspaceListResponse,
    WorkspaceSummary,
)
from .services.auth import (
    Principal,
    authenticate,
    create_account,
    create_workspace,
    issue_session,
    list_workspaces,
    principal_from_token,
    principal_workspaces,
    revoke_session,
    _rate_key,
    consume_rate_limit,
    record_security_event,
    LOGIN_RATE_LIMIT_IP,
    LOGIN_RATE_LIMIT_EMAIL,
    LOGIN_RATE_LIMIT_WINDOW,
    SIGNUP_RATE_LIMIT_IP,
    SIGNUP_RATE_LIMIT_EMAIL,
    SIGNUP_RATE_LIMIT_WINDOW,
    user_can_access_workspace,
)
from .services.onboarding import get_dataset, onboard
from .services.overview import build_overview
from .services.explore import build_explore
from .services.insights import build_insights
from .services.ask import answer_question
from .services.actions import build_actions
from .services.report import build_report
from .services.session import create_session, get_session, replace_dataset, update_scope, reset_scope
from .services.monitoring import list_alerts, create_rule, delete_rule, evaluate_alerts
from .services.saved_intelligence import list_saved, save_intelligence, delete_saved

app = FastAPI(title="AI Sales Analyst API", version="4.1.0-alpha.1", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.frontend_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=list(settings.trusted_hosts),
)


class SecurityHeadersMiddleware:
    """Add conservative response security headers."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not settings.security_headers_enabled:
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in headers}

                def add(name: str, value: str) -> None:
                    key = name.lower().encode("latin-1")
                    if key not in existing:
                        headers.append((name.encode("latin-1"), value.encode("latin-1")))

                add("X-Content-Type-Options", "nosniff")
                add("X-Frame-Options", "DENY")
                add("Referrer-Policy", "strict-origin-when-cross-origin")
                add("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
                if settings.is_production:
                    add("Strict-Transport-Security", f"max-age={settings.hsts_max_age}; includeSubDomains")
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


app.add_middleware(SecurityHeadersMiddleware)


COOKIE_SECURE = settings.secure_cookie
COOKIE_NAME = settings.cookie_name
COOKIE_MAX_AGE = 7 * 24 * 60 * 60


def _auth_user(principal: Principal) -> AuthUser:
    workspaces = [AuthWorkspace(**item) for item in principal_workspaces(principal)]
    return AuthUser(
        id=principal.user_id,
        email=principal.email,
        name=principal.name,
        organization_id=principal.organization_id,
        organization_name=principal.organization_name,
        role=principal.role,
        workspace_id=principal.workspace_id,
        workspace_name=principal.workspace_name,
        workspaces=workspaces,
    )


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def require_user(token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None) -> Principal:
    principal = principal_from_token(token)
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return principal


def _workspace(principal: Principal, workspace_id: str | None) -> str:
    selected = (workspace_id or principal.workspace_id).strip()
    if not user_can_access_workspace(principal.user_id, principal.organization_id, selected):
        raise HTTPException(status_code=403, detail="Workspace is not available to this organization member.")
    return selected


def _dataset_for(principal: Principal, dataset_id: str):
    summary = get_dataset(dataset_id, organization_id=principal.organization_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if summary.workspace_id and not user_can_access_workspace(principal.user_id, principal.organization_id, summary.workspace_id):
        raise HTTPException(status_code=403, detail="Dataset is not available to this organization member.")
    return summary


def _session_for(principal: Principal, session_id: str, dataset_id: str | None = None):
    current = get_session(session_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    if current.organization_id != principal.organization_id:
        raise HTTPException(status_code=403, detail="Analysis session is not available to this organization member.")
    if current.workspace_id and not user_can_access_workspace(principal.user_id, principal.organization_id, current.workspace_id):
        raise HTTPException(status_code=403, detail="Analysis session is not available to this workspace.")
    if dataset_id and current.dataset_id != dataset_id:
        raise HTTPException(status_code=409, detail="Analysis session does not match the dataset.")
    return current


def _scope_for(principal: Principal, dataset_id: str, session_id: str | None):
    _dataset_for(principal, dataset_id)
    if not session_id:
        return None
    return _session_for(principal, session_id, dataset_id).scope


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", product="AI Sales Analyst", version="4.1.0-alpha.1")


@app.post("/api/v1/auth/signup", response_model=AuthResponse)
def signup(request: SignupRequest, response: Response, http_request: Request) -> AuthResponse:
    client_ip = http_request.client.host if http_request.client else "unknown"
    email = request.email.strip().lower()
    ip_allowed = consume_rate_limit("signup", _rate_key("ip", client_ip), SIGNUP_RATE_LIMIT_IP, SIGNUP_RATE_LIMIT_WINDOW)
    email_allowed = consume_rate_limit("signup", _rate_key("email", email), SIGNUP_RATE_LIMIT_EMAIL, SIGNUP_RATE_LIMIT_WINDOW)
    if not ip_allowed or not email_allowed:
        record_security_event("signup_rate_limited", email=email, client_ip=client_ip)
        raise HTTPException(status_code=429, detail="Too many signup attempts. Please try again later.")
    try:
        principal = create_account(request.email, request.password, request.name, request.organization_name)
        token, _ = issue_session(principal.user_id)
        _set_session_cookie(response, token)
        record_security_event("signup_success", email=principal.email, client_ip=client_ip, user_id=principal.user_id)
        return AuthResponse(user=_auth_user(principal))
    except ValueError as exc:
        # Keep the public response generic so account existence cannot be enumerated.
        if "already exists" in str(exc).lower():
            record_security_event("signup_duplicate", email=email, client_ip=client_ip)
            raise HTTPException(status_code=400, detail="Unable to create this account.") from exc
        record_security_event("signup_rejected", email=email, client_ip=client_ip)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/auth/login", response_model=AuthResponse)
def login(request: LoginRequest, response: Response, http_request: Request) -> AuthResponse:
    client_ip = http_request.client.host if http_request.client else "unknown"
    email = request.email.strip().lower()
    ip_allowed = consume_rate_limit("login", _rate_key("ip", client_ip), LOGIN_RATE_LIMIT_IP, LOGIN_RATE_LIMIT_WINDOW)
    email_allowed = consume_rate_limit("login", _rate_key("email", email), LOGIN_RATE_LIMIT_EMAIL, LOGIN_RATE_LIMIT_WINDOW)
    if not ip_allowed or not email_allowed:
        record_security_event("login_rate_limited", email=email, client_ip=client_ip)
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    try:
        principal = authenticate(request.email, request.password)
        token, _ = issue_session(principal.user_id)
        _set_session_cookie(response, token)
        record_security_event("login_success", email=principal.email, client_ip=client_ip, user_id=principal.user_id)
        return AuthResponse(user=_auth_user(principal))
    except ValueError as exc:
        record_security_event("login_failed", email=email, client_ip=client_ip)
        raise HTTPException(status_code=401, detail="Email or password is incorrect.") from exc


@app.get("/api/v1/auth/me", response_model=AuthResponse)
def me(principal: Principal = Depends(require_user)) -> AuthResponse:
    return AuthResponse(user=_auth_user(principal))


@app.post("/api/v1/auth/logout")
def logout(response: Response, token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None):
    revoke_session(token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@app.get("/api/v1/workspaces", response_model=WorkspaceListResponse)
def workspaces(principal: Principal = Depends(require_user)) -> WorkspaceListResponse:
    return WorkspaceListResponse(
        organization_id=principal.organization_id,
        items=[WorkspaceSummary(**item) for item in list_workspaces(principal.organization_id)],
    )


@app.post("/api/v1/workspaces", response_model=WorkspaceSummary)
def add_workspace(request: CreateWorkspaceRequest, principal: Principal = Depends(require_user)) -> WorkspaceSummary:
    if principal.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Only organization owners or admins can create workspaces.")
    try:
        return WorkspaceSummary(**create_workspace(principal.organization_id, request.name))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/onboarding/profile", response_model=OnboardingResponse)
async def profile_upload(
    file: UploadFile = File(...),
    workspace_id: str | None = None,
    principal: Principal = Depends(require_user),
) -> OnboardingResponse:
    selected_workspace = _workspace(principal, workspace_id)
    try:
        summary = onboard(file.filename or "upload", file.file, organization_id=principal.organization_id, workspace_id=selected_workspace)
        session = create_session(summary.dataset_id, organization_id=principal.organization_id, workspace_id=selected_workspace)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not understand this file: {exc}") from exc
    return OnboardingResponse(dataset=summary, message="Your dataset is ready for analysis.", session_id=session.session_id)

@app.get("/api/v1/datasets/{dataset_id}")
def dataset(dataset_id: str, principal: Principal = Depends(require_user)):
    return _dataset_for(principal, dataset_id)


@app.get("/api/v1/datasets/{dataset_id}/overview", response_model=OverviewResponse)
def overview(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user)) -> OverviewResponse:
    try:
        return build_overview(dataset_id, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build overview: {exc}") from exc


@app.get("/api/v1/datasets/{dataset_id}/explore", response_model=ExploreResponse)
def explore(dataset_id: str, metric: str | None = None, dimension: str | None = None, limit: int = 8, session_id: str | None = None, principal: Principal = Depends(require_user)) -> ExploreResponse:
    try:
        return build_explore(dataset_id, metric, dimension, limit, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build exploration: {exc}") from exc


@app.get("/api/v1/datasets/{dataset_id}/insights", response_model=InsightsResponse)
def insights(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user)) -> InsightsResponse:
    try:
        return build_insights(dataset_id, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build insights: {exc}") from exc


@app.post("/api/v1/datasets/{dataset_id}/ask", response_model=AskResponse)
def ask(dataset_id: str, question: str, session_id: str | None = None, principal: Principal = Depends(require_user)) -> AskResponse:
    try:
        return answer_question(dataset_id, question, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not answer the question: {exc}") from exc


@app.get("/api/v1/datasets/{dataset_id}/actions", response_model=ActionsResponse)
def actions(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user)) -> ActionsResponse:
    try:
        return build_actions(dataset_id, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build actions: {exc}") from exc


@app.get("/api/v1/datasets/{dataset_id}/report", response_model=ReportResponse)
def report(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user)) -> ReportResponse:
    try:
        return build_report(dataset_id, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build report: {exc}") from exc


@app.get("/api/v1/datasets/{dataset_id}/alerts", response_model=AlertsResponse)
def alerts(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user)) -> AlertsResponse:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for monitoring.")
    _session_for(principal, session_id, dataset_id)
    try:
        return list_alerts(dataset_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/datasets/{dataset_id}/alerts", response_model=AlertRule)
def create_alert(dataset_id: str, request: AlertRuleCreate, session_id: str | None = None, principal: Principal = Depends(require_user)) -> AlertRule:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for monitoring.")
    _session_for(principal, session_id, dataset_id)
    try:
        return create_rule(dataset_id, session_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/v1/datasets/{dataset_id}/alerts/{rule_id}")
def remove_alert(dataset_id: str, rule_id: str, session_id: str | None = None, principal: Principal = Depends(require_user)):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for monitoring.")
    _session_for(principal, session_id, dataset_id)
    try:
        delete_rule(dataset_id, session_id, rule_id)
        return {"status": "ok"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/datasets/{dataset_id}/alerts/evaluate", response_model=AlertsResponse)
def evaluate_dataset_alerts(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user)) -> AlertsResponse:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for monitoring.")
    _session_for(principal, session_id, dataset_id)
    try:
        return evaluate_alerts(dataset_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/sessions", response_model=AnalysisSession)
def create_session_endpoint(body: dict, principal: Principal = Depends(require_user)) -> AnalysisSession:
    dataset_id = str(body.get("dataset_id") or "").strip()
    workspace_id = str(body.get("workspace_id") or principal.workspace_id).strip()
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required.")
    _workspace(principal, workspace_id)
    _dataset_for(principal, dataset_id)
    try:
        return create_session(dataset_id, organization_id=principal.organization_id, workspace_id=workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/{session_id}", response_model=AnalysisSession)
def session(session_id: str, principal: Principal = Depends(require_user)) -> AnalysisSession:
    return _session_for(principal, session_id)


@app.post("/api/v1/sessions/{session_id}/dataset/{dataset_id}", response_model=AnalysisSession)
def session_dataset(session_id: str, dataset_id: str, principal: Principal = Depends(require_user)) -> AnalysisSession:
    target = _dataset_for(principal, dataset_id)
    current = _session_for(principal, session_id)
    if current.workspace_id and target.workspace_id and current.workspace_id != target.workspace_id:
        raise HTTPException(status_code=409, detail="Replacement dataset must belong to the current workspace.")
    try:
        return replace_dataset(session_id, dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/sessions/{session_id}/scope", response_model=AnalysisSession)
def session_scope(session_id: str, body: dict, principal: Principal = Depends(require_user)) -> AnalysisSession:
    _session_for(principal, session_id)
    try:
        filters = [ScopeFilter.model_validate(item) for item in body.get("filters", [])]
        return update_scope(session_id, filters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/sessions/{session_id}/scope-values", response_model=ScopeValuesResponse)
def session_scope_values(session_id: str, field: str, limit: int = 100, principal: Principal = Depends(require_user)) -> ScopeValuesResponse:
    from .services.session import scope_values
    _session_for(principal, session_id)
    try:
        values = scope_values(session_id, field, limit)
        return ScopeValuesResponse(field=field, values=[ScopeValue(value=v, label=v) for v in values])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/sessions/{session_id}/scope/reset", response_model=AnalysisSession)
def session_scope_reset(session_id: str, principal: Principal = Depends(require_user)) -> AnalysisSession:
    _session_for(principal, session_id)
    try:
        return reset_scope(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/datasets/{dataset_id}/saved", response_model=SavedIntelligenceResponse)
def saved(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user)) -> SavedIntelligenceResponse:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for saved intelligence.")
    _session_for(principal, session_id, dataset_id)
    try:
        return list_saved(dataset_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/datasets/{dataset_id}/saved", response_model=SavedIntelligence)
def save(dataset_id: str, request: SavedIntelligenceCreate, session_id: str | None = None, principal: Principal = Depends(require_user)) -> SavedIntelligence:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for saved intelligence.")
    _session_for(principal, session_id, dataset_id)
    try:
        return save_intelligence(dataset_id, session_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/v1/datasets/{dataset_id}/saved/{item_id}")
def remove_saved(dataset_id: str, item_id: str, session_id: str | None = None, principal: Principal = Depends(require_user)):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for saved intelligence.")
    _session_for(principal, session_id, dataset_id)
    try:
        delete_saved(dataset_id, session_id, item_id)
        return {"status": "ok"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
