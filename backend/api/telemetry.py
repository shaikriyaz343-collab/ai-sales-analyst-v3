import contextvars
import json
import logging
import re
import time
import uuid

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9-]{1,64}$")

request_id_var = contextvars.ContextVar("request_id", default=None)
user_id_var = contextvars.ContextVar("user_id", default=None)
org_id_var = contextvars.ContextVar("org_id", default=None)

METRIC_REGISTRY = {
    "http_requests_total": {
        "type": "counter",
        "unit": "count",
        "labels": {"method": None, "route": None, "status_code": None},
    },
    "http_request_duration_seconds": {
        "type": "histogram",
        "unit": "seconds",
        "labels": {"method": None, "route": None},
    },
    "http_5xx_total": {
        "type": "counter",
        "unit": "count",
        "labels": {"method": None, "route": None, "status_code": None},
    },
    "auth_failures_total": {
        "type": "counter",
        "unit": "count",
        "labels": {"route": None, "reason": {"invalid_token", "missing_token"}},
    },
    "rate_limit_hits_total": {
        "type": "counter",
        "unit": "count",
        "labels": {"route": None},
    },
    "database_pool_timeouts_total": {
        "type": "counter",
        "unit": "count",
        "labels": {"pool_name": {"default"}},
    },
    "database_failures_total": {
        "type": "counter",
        "unit": "count",
        "labels": {"operation": {"query", "transaction"}, "failure_type": {"connection", "statement"}},
    },
    "object_store_failures_total": {
        "type": "counter",
        "unit": "count",
        "labels": {"operation": {"read", "write"}, "failure_type": {"timeout", "client_error"}},
    },
    "migration_status": {
        "type": "state",
        "unit": "state",
        "labels": {"target_version": None, "status": {"success", "failure"}},
    }
}

FORBIDDEN_LABELS = {
    "request_id", "session_id", "user_id", "organization_id", "dataset_id",
    "email", "raw_url", "query_string", "sql", "exception", "traceback"
}

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.organization_id = org_id_var.get()
        return True

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if getattr(record, "request_id", None):
            log_record["request_id"] = record.request_id

        if getattr(record, "user_id", None):
            log_record["user_id"] = record.user_id

        if getattr(record, "organization_id", None):
            log_record["organization_id"] = record.organization_id

        if hasattr(record, "http_info"):
            log_record.update(record.http_info)

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)

class MetricJSONFormatter(logging.Formatter):
    def format(self, record):
        if hasattr(record, "metric_payload"):
            return json.dumps(record.metric_payload)
        return json.dumps({"message": record.getMessage()})

def emit_metric(name: str, value: float | int, labels: dict):
    if name not in METRIC_REGISTRY:
        raise ValueError(f"Unknown metric: {name}")

    spec = METRIC_REGISTRY[name]

    for k in labels:
        if k in FORBIDDEN_LABELS:
            raise ValueError(f"Forbidden metric label: {k}")
        if k not in spec["labels"]:
            raise ValueError(f"Unknown label key '{k}' for metric '{name}'")

    for k in spec["labels"]:
        if k not in labels:
            raise ValueError(f"Missing required label '{k}' for metric '{name}'")

    for k, v in labels.items():
        allowed = spec["labels"][k]
        if allowed is not None and v not in allowed:
            raise ValueError(f"Invalid value '{v}' for label '{k}' in metric '{name}'")

    if not isinstance(value, (int, float)):
        raise ValueError("Metric value must be numeric")

    payload = {
        "telemetry_version": 1,
        "event_type": "metric",
        "metric_name": name,
        "metric_type": spec["type"],
        "value": value,
        "unit": spec["unit"],
        "labels": labels
    }

    metrics_logger = logging.getLogger("ai_sales_analyst.metrics")
    metrics_logger.info("METRIC", extra={"metric_payload": payload})


def safe_emit_metric(name: str, value: float | int, labels: dict):
    try:
        emit_metric(name, value, labels)
    except Exception as e:
        error_logger = logging.getLogger("ai_sales_analyst.errors")
        # Safely log the metric name and exception type, avoiding raw values to prevent PII leakage
        error_logger.error(f"Telemetry emission failed for metric '{name}': {type(e).__name__}")

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    ctx_filter = ContextFilter()

    for name in ["ai_sales_analyst.errors", "ai_sales_analyst.access"]:
        l = logging.getLogger(name)
        l.handlers = [handler]
        l.setLevel(logging.INFO)
        l.propagate = False
        l.addFilter(ctx_filter)

    metric_handler = logging.StreamHandler()
    metric_handler.setFormatter(MetricJSONFormatter())
    ml = logging.getLogger("ai_sales_analyst.metrics")
    ml.handlers = [metric_handler]
    ml.setLevel(logging.INFO)
    ml.propagate = False

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.propagate = False
    uvicorn_access.handlers = [h for h in uvicorn_access.handlers if "pytest" in str(type(h)).lower() or "logcapture" in str(type(h)).lower()]

class CorrelationMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("ai_sales_analyst.access")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = dict(scope.get("headers", []))
        req_id_bytes = headers.get(b"x-request-id")
        req_id = req_id_bytes.decode("ascii") if req_id_bytes else None

        if not req_id or not SAFE_ID_REGEX.match(req_id):
            req_id = uuid.uuid4().hex

        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = req_id

        token_req = request_id_var.set(req_id)
        token_uid = user_id_var.set(None)
        token_oid = org_id_var.set(None)

        start_time = time.perf_counter()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                msg_headers = list(message.get("headers", []))
                msg_headers.append((b"x-request-id", req_id.encode("ascii")))
                message["headers"] = msg_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            route = scope.get("route")
            route_path = route.path if route and hasattr(route, "path") else "unmatched_route"
            method = scope.get("method", "GET")

            http_info = {
                "method": method,
                "route": route_path,
                "status": status_code,
                "duration_ms": round(duration_ms, 2)
            }
            self.logger.info("HTTP Request", extra={"http_info": http_info})

            try:
                safe_emit_metric("http_requests_total", 1, {
                    "method": method,
                    "route": route_path,
                    "status_code": status_code
                })

                safe_emit_metric("http_request_duration_seconds", round(duration_ms / 1000, 4), {
                    "method": method,
                    "route": route_path
                })

                if status_code >= 500:
                    safe_emit_metric("http_5xx_total", 1, {
                        "method": method,
                        "route": route_path,
                        "status_code": status_code
                    })
            finally:
                request_id_var.reset(token_req)
                user_id_var.reset(token_uid)
                org_id_var.reset(token_oid)
