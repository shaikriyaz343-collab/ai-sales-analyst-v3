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

            route_path = scope.get("route").path if "route" in scope else scope.get("path", "unknown")
            method = scope.get("method", "GET")

            http_info = {
                "method": method,
                "route": route_path,
                "status": status_code,
                "duration_ms": round(duration_ms, 2)
            }
            self.logger.info("HTTP Request", extra={"http_info": http_info})

            request_id_var.reset(token_req)
            user_id_var.reset(token_uid)
            org_id_var.reset(token_oid)
