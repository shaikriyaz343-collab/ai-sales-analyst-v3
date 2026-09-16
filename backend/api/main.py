from __future__ import annotations

from contextlib import asynccontextmanager
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
from .persistence import PersistenceConfigurationError

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

@app.exception_handler(PersistenceConfigurationError)
async def persistence_configuration_exception_handler(request: Request, exc: PersistenceConfigurationError):
    from backend.api.telemetry import safe_emit_metric
    op = "write" if request.method in ("POST", "PUT", "PATCH", "DELETE") else "read"
    safe_emit_metric("object_store_failures_total", 1, {"operation": op, "failure_type": "configuration"})
    logger.error(_sanitize_log(f"Object storage configuration failure: {exc}"))
    return JSONResponse(status_code=503, content={"detail": "Service Unavailable - Object storage failed."})

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
