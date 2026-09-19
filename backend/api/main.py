from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import enum
from typing import Annotated

import anyio

from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile

class LifecycleState(enum.Enum):
    STARTING = "STARTING"
    READY = "READY"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    FAILED = "FAILED"

class AppState:
    lifecycle: LifecycleState = LifecycleState.STARTING

app_state = AppState()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .config import settings
from .persistence import PersistenceConfigurationError
from .contracts import (
    ActionItem,
    ActionStatusUpdate,
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
    ForecastResponse,
    HealthResponse,
    InsightsResponse,
    LoginRequest,
    OnboardingResponse,
    OverviewResponse,
    ReadyResponse,
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
    revoke_all_sessions,
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
from .services.forecast import build_forecast
from .services.insights import build_insights
from .services.ask import answer_question
from .services.actions import build_actions
from .services.action_workflow import update_action_status
from .services.report import build_report
from .services.session import create_session, get_session, replace_dataset, update_scope, reset_scope
from .services.monitoring import list_alerts, create_rule, delete_rule, evaluate_alerts
from .services.saved_intelligence import list_saved, save_intelligence, delete_saved
from .services.commercial import plan_catalog
from .services.commercial_store import runtime_commercial_repository, reset_runtime_commercial_repository
from .services.payment_provider import PaddleProvider, PaymentProviderError, CheckoutRequest

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.analytics_limiter = anyio.CapacityLimiter(settings.analytics_concurrency)
    app_state.lifecycle = LifecycleState.STARTING
    if settings.persistence_mode == "external":
        from . import runtime_persistence
        from .services.auth import set_external_auth, reset_external_auth
        from .services.auth_postgres import PostgresAuthStore

        try:
            runtime_persistence.start_runtime_persistence()
            auth_store = PostgresAuthStore(settings.database_url, provider=runtime_persistence._provider)
            set_external_auth(auth_store)
            app_state.lifecycle = LifecycleState.READY
            yield
        except Exception:
            app_state.lifecycle = LifecycleState.FAILED
            raise
        finally:
            app_state.lifecycle = LifecycleState.SHUTTING_DOWN
            reset_external_auth()
            reset_runtime_commercial_repository()
            runtime_persistence.reset_runtime_persistence()
            app.state.analytics_limiter = None
    else:
        from .runtime_persistence import start_runtime_persistence, reset_runtime_persistence
        try:
            start_runtime_persistence()
            app_state.lifecycle = LifecycleState.READY
            yield
        except Exception:
            app_state.lifecycle = LifecycleState.FAILED
            raise
        finally:
            app_state.lifecycle = LifecycleState.SHUTTING_DOWN
            reset_runtime_commercial_repository()
            reset_runtime_persistence()
            app.state.analytics_limiter = None

app = FastAPI(title="AI Sales Analyst API", version="4.1.0-alpha.1", docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)
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

import logging
import psycopg

async def require_analysis_capacity(request: Request):
    limiter = request.app.state.analytics_limiter
    try:
        limiter.acquire_nowait()
    except anyio.WouldBlock:
        raise HTTPException(
            status_code=503,
            detail="Analytics engine is currently at maximum capacity."
        )

    try:
        yield
    finally:
        limiter.release()

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .telemetry import setup_logging, CorrelationMiddleware, user_id_var, org_id_var
setup_logging()
app.add_middleware(CorrelationMiddleware)

try:
    from botocore.exceptions import BotoCoreError, ClientError
    _has_boto = True
except ImportError:
    _has_boto = False

logger = logging.getLogger("ai_sales_analyst.errors")


def _payment_provider() -> PaddleProvider | None:
    if settings.billing_provider != "paddle":
        return None
    return PaddleProvider(
        api_key=settings.paddle_api_key or "",
        webhook_secret=settings.paddle_webhook_secret or "",
        environment=settings.paddle_environment,
        starter_price_id=settings.paddle_starter_price_id or "",
        growth_price_id=settings.paddle_growth_price_id or "",
    )


def _record_commercial_usage(organization_id: str, metric: str) -> None:
    """Record non-blocking commercial usage telemetry on successful user actions."""
    try:
        runtime_commercial_repository().record_usage(
            organization_id,
            metric,
            now=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.warning("Commercial usage meter unavailable for %s: %s", metric, _sanitize_log(str(exc)))


def _sanitize_log(text: str) -> str:
    if not text:
        return text
    secrets = []
    if settings.database_url:
        secrets.append(settings.database_url)
    if settings.object_store_secret_key:
        secrets.append(settings.object_store_secret_key)
    if settings.object_store_access_key:
        secrets.append(settings.object_store_access_key)

    for s in secrets:
        if s and len(s) > 4:
            text = text.replace(s, "***REDACTED***")
    return text

@app.exception_handler(psycopg.OperationalError)
async def psycopg_operational_exception_handler(request: Request, exc: psycopg.OperationalError):
    from backend.api.telemetry import safe_emit_metric
    try:
        import psycopg_pool
        if isinstance(exc, psycopg_pool.PoolTimeout):
            safe_emit_metric("database_pool_timeouts_total", 1, {"pool_name": "default"})
        else:
            op = "transaction" if request.method in ("POST", "PUT", "PATCH", "DELETE") else "query"
            safe_emit_metric("database_failures_total", 1, {"operation": op, "failure_type": "connection"})
    except ImportError:
        op = "transaction" if request.method in ("POST", "PUT", "PATCH", "DELETE") else "query"
        safe_emit_metric("database_failures_total", 1, {"operation": op, "failure_type": "connection"})

    logger.error(_sanitize_log(f"Database dependency failure: {exc}"))
    return JSONResponse(status_code=503, content={"detail": "Service Unavailable - Database connection failed."})

if _has_boto:
    @app.exception_handler(BotoCoreError)
    async def botocore_exception_handler(request: Request, exc: BotoCoreError):
        from backend.api.telemetry import safe_emit_metric
        op = "write" if request.method in ("POST", "PUT", "PATCH", "DELETE") else "read"
        failure_type = "timeout" if "timeout" in str(type(exc)).lower() else "client_error"
        safe_emit_metric("object_store_failures_total", 1, {"operation": op, "failure_type": failure_type})
        logger.error(_sanitize_log(f"Object storage dependency failure: {exc}"))
        return JSONResponse(status_code=503, content={"detail": "Service Unavailable - Object storage failed."})

    @app.exception_handler(ClientError)
    async def botocore_client_exception_handler(request: Request, exc: ClientError):
        from backend.api.telemetry import safe_emit_metric
        op = "write" if request.method in ("POST", "PUT", "PATCH", "DELETE") else "read"
        failure_type = "timeout" if "timeout" in str(type(exc)).lower() else "client_error"
        safe_emit_metric("object_store_failures_total", 1, {"operation": op, "failure_type": failure_type})
        logger.error(_sanitize_log(f"Object storage client failure: {exc}"))
        return JSONResponse(status_code=503, content={"detail": "Service Unavailable - Object storage failed."})

@app.exception_handler(PersistenceConfigurationError)
async def persistence_configuration_exception_handler(request: Request, exc: PersistenceConfigurationError):
    from backend.api.telemetry import safe_emit_metric
    op = "write" if request.method in ("POST", "PUT", "PATCH", "DELETE") else "read"
    safe_emit_metric("object_store_failures_total", 1, {"operation": op, "failure_type": "configuration"})
    logger.error(_sanitize_log(f"Object storage configuration/dependency failure: {exc}"))
    return JSONResponse(status_code=503, content={"detail": "Service Unavailable - Object storage failed."})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=getattr(exc, "headers", None))
    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    import traceback
    from backend.api import telemetry
    import psycopg

    try:
        import psycopg_pool
        if isinstance(exc, psycopg_pool.PoolTimeout):
            telemetry.safe_emit_metric("database_pool_timeouts_total", 1, {"pool_name": "default"})
    except ImportError:
        pass

    if isinstance(exc, psycopg.Error):
        op = "transaction" if request.method in ("POST", "PUT", "PATCH", "DELETE") else "query"
        failure_type = "connection" if isinstance(exc, psycopg.OperationalError) else "statement"
        telemetry.safe_emit_metric("database_failures_total", 1, {"operation": op, "failure_type": failure_type})

    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    req_id = request.scope.get("state", {}).get("request_id")
    token = telemetry.request_id_var.set(req_id) if req_id else None

    try:
        logger.error(_sanitize_log(f"Unexpected internal error: {exc}\n{tb_str}"))
    finally:
        if token:
            telemetry.request_id_var.reset(token)

    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
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
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


def require_user(request: Request, token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None) -> Principal:
    route = request.scope.get("route")
    route_path = route.path if route and hasattr(route, "path") else "unmatched_route"
    if not token:
        from backend.api.telemetry import safe_emit_metric
        safe_emit_metric("auth_failures_total", 1, {"route": route_path, "reason": "missing_token"})
        raise HTTPException(status_code=401, detail="Authentication required.")
    principal = principal_from_token(token)
    if principal is None:
        from backend.api.telemetry import safe_emit_metric
        safe_emit_metric("auth_failures_total", 1, {"route": route_path, "reason": "invalid_token"})
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_id_var.set(principal.user_id)
    org_id_var.set(principal.organization_id)
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
async def health() -> HealthResponse:
    return HealthResponse(status="ok", product="AI Sales Analyst", version="4.1.0-alpha.1")


@app.get("/api/v1/ready", response_model=ReadyResponse)
def ready(response: Response) -> ReadyResponse:
    if app_state.lifecycle != LifecycleState.READY:
        response.status_code = 503
        return ReadyResponse(status="not_ready", reason=app_state.lifecycle.value.lower())

    if settings.persistence_mode == "external":
        try:
            from . import runtime_persistence
            provider = runtime_persistence._provider
            if not provider:
                response.status_code = 503
                return ReadyResponse(status="not_ready", reason="provider_missing")
            provider.check()
        except Exception:
            response.status_code = 503
            return ReadyResponse(status="not_ready", reason="database_down")

    return ReadyResponse(status="ready")


@app.post("/api/v1/auth/signup", response_model=AuthResponse)
def signup(request: SignupRequest, response: Response, http_request: Request) -> AuthResponse:
    client_ip = http_request.client.host if http_request.client else "unknown"
    email = request.email.strip().lower()
    ip_allowed = consume_rate_limit("signup", _rate_key("ip", client_ip), SIGNUP_RATE_LIMIT_IP, SIGNUP_RATE_LIMIT_WINDOW)
    email_allowed = consume_rate_limit("signup", _rate_key("email", email), SIGNUP_RATE_LIMIT_EMAIL, SIGNUP_RATE_LIMIT_WINDOW)
    if not ip_allowed or not email_allowed:
        from backend.api.telemetry import safe_emit_metric
        safe_emit_metric("rate_limit_hits_total", 1, {"route": "/api/v1/auth/signup"})
        record_security_event("signup_rate_limited", email=email, client_ip=client_ip)
        raise HTTPException(status_code=429, detail="Too many signup attempts. Please try again later.")
    try:
        principal = create_account(request.email, request.password, request.name, request.organization_name)
        token, _ = issue_session(principal.user_id)
        _set_session_cookie(response, token)
        record_security_event("signup_success", email=principal.email, client_ip=client_ip, user_id=principal.user_id)
        return AuthResponse(user=_auth_user(principal))
    except ValueError as exc:
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
        from backend.api.telemetry import safe_emit_metric
        safe_emit_metric("rate_limit_hits_total", 1, {"route": "/api/v1/auth/login"})
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


@app.post("/api/v1/auth/sessions/revoke-all")
def revoke_all_auth_sessions(principal: Principal = Depends(require_user)):
    revoked = revoke_all_sessions(principal.user_id)
    return {"status": "ok", "revoked": revoked}


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
        _record_commercial_usage(principal.organization_id, "dataset_uploads")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OnboardingResponse(dataset=summary, message="Your dataset is ready for analysis.", session_id=session.session_id)

@app.get("/api/v1/datasets/{dataset_id}")
def dataset(dataset_id: str, principal: Principal = Depends(require_user)):
    return _dataset_for(principal, dataset_id)


@app.get("/api/v1/datasets/{dataset_id}/overview", response_model=OverviewResponse)
def overview(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> OverviewResponse:
    try:
        return build_overview(dataset_id, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/datasets/{dataset_id}/explore", response_model=ExploreResponse)
def explore(dataset_id: str, metric: str | None = None, dimension: str | None = None, limit: int = 8, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> ExploreResponse:
    try:
        return build_explore(dataset_id, metric, dimension, limit, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/datasets/{dataset_id}/forecast", response_model=ForecastResponse)
def forecast(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> ForecastResponse:
    try:
        return build_forecast(dataset_id, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/datasets/{dataset_id}/insights", response_model=InsightsResponse)
def insights(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> InsightsResponse:
    try:
        return build_insights(dataset_id, scope=_scope_for(principal, dataset_id, session_id))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/datasets/{dataset_id}/ask", response_model=AskResponse)
def ask(dataset_id: str, question: str, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> AskResponse:
    try:
        result = answer_question(dataset_id, question, scope=_scope_for(principal, dataset_id, session_id))
        _record_commercial_usage(principal.organization_id, "analyst_questions")
        return result
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/datasets/{dataset_id}/actions", response_model=ActionsResponse)
def actions(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> ActionsResponse:
    try:
        scope = _scope_for(principal, dataset_id, session_id)
        return build_actions(dataset_id, scope=scope, session_id=session_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/datasets/{dataset_id}/actions/{action_id}/status", response_model=ActionItem)
def update_dataset_action_status(
    dataset_id: str,
    action_id: str,
    request: ActionStatusUpdate,
    session_id: str | None = None,
    principal: Principal = Depends(require_user),
) -> ActionItem:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for action workflow updates.")
    _session_for(principal, session_id, dataset_id)
    try:
        return update_action_status(dataset_id, session_id, action_id, request.status)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "no longer available" in message.lower() or "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@app.get("/api/v1/datasets/{dataset_id}/report", response_model=ReportResponse)
def report(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> ReportResponse:
    try:
        result = build_report(dataset_id, scope=_scope_for(principal, dataset_id, session_id))
        _record_commercial_usage(principal.organization_id, "reports")
        return result
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
        result = create_rule(dataset_id, session_id, request)
        _record_commercial_usage(principal.organization_id, "monitoring_rules")
        return result
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
def evaluate_dataset_alerts(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> AlertsResponse:
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
def saved(dataset_id: str, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> SavedIntelligenceResponse:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for saved intelligence.")
    _session_for(principal, session_id, dataset_id)
    try:
        return list_saved(dataset_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/datasets/{dataset_id}/saved", response_model=SavedIntelligence)
def save(dataset_id: str, request: SavedIntelligenceCreate, session_id: str | None = None, principal: Principal = Depends(require_user), _cap: None = Depends(require_analysis_capacity)) -> SavedIntelligence:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for saved intelligence.")
    _session_for(principal, session_id, dataset_id)
    try:
        result = save_intelligence(dataset_id, session_id, request)
        _record_commercial_usage(principal.organization_id, "saved_intelligence")
        return result
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


@app.get("/api/v1/commercial/entitlements")
def commercial_entitlements(principal: Principal = Depends(require_user)) -> dict[str, object]:
    """Return the current organization-level commercial state without mutating product entitlements."""
    now = datetime.now(timezone.utc)
    repository = runtime_commercial_repository()
    snapshot = repository.get_entitlements(principal.organization_id, now=now)
    subscription = repository.find_subscription(principal.organization_id)
    return {
        "organization_id": snapshot.organization_id,
        "subscription": {
            "plan_id": snapshot.plan_id,
            "plan_name": snapshot.plan_name,
            "access_active": snapshot.access_active,
            "access_reason": snapshot.access_reason,
            "status": subscription.status if subscription else snapshot.access_reason,
            "provider": subscription.provider if subscription else None,
            "provider_subscription_id": subscription.provider_subscription_id if subscription else None,
        },
        "entitlements": {
            "max_seats": snapshot.max_seats,
            "max_workspaces": snapshot.max_workspaces,
            "features": sorted(snapshot.features),
            "remaining": snapshot.remaining,
        },
        "usage_period_start": snapshot.usage.period_start.isoformat() if snapshot.usage.period_start else None,
        "usage": snapshot.usage.counts,
        "billing": {
            "provider": settings.billing_provider,
            "checkout_ready": settings.billing_provider == "paddle",
            "customer_portal_available": bool(
                subscription and subscription.provider == "paddle" and subscription.provider_customer_id
            ),
        },
        "catalog": [
            {
                "plan_id": plan.plan_id,
                "name": plan.name,
                "price_usd_monthly": plan.price_usd_monthly,
                "trial_days": plan.trial_days,
                "max_seats": plan.max_seats,
                "max_workspaces": plan.max_workspaces,
                "monthly_limits": plan.monthly_limits,
                "features": sorted(plan.features),
            }
            for plan in plan_catalog()
        ],
    }


@app.post("/api/v1/commercial/checkout")
def commercial_checkout(
    payload: dict[str, str],
    principal: Principal = Depends(require_user),
) -> dict[str, str]:
    provider = _payment_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="Billing checkout is not configured yet.")
    plan_id = str(payload.get("plan_id") or "")
    if plan_id not in {"starter", "growth"}:
        raise HTTPException(status_code=400, detail="A paid plan must be selected.")

    frontend_origin = settings.frontend_origins[0].rstrip("/")
    try:
        session = provider.create_checkout_session(
            CheckoutRequest(
                organization_id=principal.organization_id,
                plan_id=plan_id,
                customer_email=principal.email,
                customer_name=principal.name,
                success_url=f"{frontend_origin}/dashboard/billing?checkout=success",
                cancel_url=f"{frontend_origin}/dashboard/billing?checkout=cancelled",
            )
        )
    except PaymentProviderError as exc:
        logger.warning("Commercial checkout unavailable: %s", _sanitize_log(str(exc)))
        raise HTTPException(status_code=502, detail="Checkout could not be started.") from exc

    return {
        "provider": session.provider,
        "provider_session_id": session.provider_session_id,
        "checkout_url": session.checkout_url,
    }


@app.get("/api/v1/commercial/portal")
def commercial_portal(principal: Principal = Depends(require_user)) -> dict[str, str]:
    provider = _payment_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="Billing provider is not configured.")
    subscription = runtime_commercial_repository().find_subscription(principal.organization_id)
    if not subscription or subscription.provider != provider.name or not subscription.provider_customer_id:
        raise HTTPException(status_code=409, detail="No active provider billing account is linked yet.")

    try:
        url = provider.get_customer_portal_url(
            subscription.provider_customer_id,
            f"{settings.frontend_origins[0].rstrip('/')}/dashboard/billing",
        )
    except PaymentProviderError as exc:
        logger.warning("Customer portal unavailable: %s", _sanitize_log(str(exc)))
        raise HTTPException(status_code=502, detail="Customer portal could not be opened.") from exc
    return {"portal_url": url}


@app.post("/api/v1/commercial/webhook")
async def commercial_webhook(request: Request) -> dict[str, object]:
    provider = _payment_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="Billing provider is not configured.")

    signature = request.headers.get("Paddle-Signature", "")
    body = await request.body()
    try:
        event = provider.verify_webhook(body, signature)
        applied = runtime_commercial_repository().apply_webhook_event(
            event,
            plan_for_price=provider.plan_for_price,
        )
    except (PaymentProviderError, ValueError) as exc:
        logger.warning("Commercial webhook rejected: %s", _sanitize_log(str(exc)))
        raise HTTPException(status_code=400, detail="Webhook rejected.") from exc

    return {
        "status": "ok",
        "event_id": event.event_id,
        "event_type": event.event_type,
        "applied": applied,
    }
