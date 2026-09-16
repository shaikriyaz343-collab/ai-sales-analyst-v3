from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..contracts import AlertEvent, AlertRule, AlertsResponse, AlertRuleCreate, Evidence
from ..runtime_persistence import runtime_document_store
from .onboarding import get_dataset, STORAGE
from .overview import build_overview
from .session import require_session, scope_label

MONITORING_STORAGE = STORAGE.parent / "runtime_monitoring"
OPS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "eq": "=", "neq": "≠"}
SUPPORTED_CADENCES = {"manual", "daily", "weekly"}
CADENCE_INTERVALS = {"daily": timedelta(days=1), "weekly": timedelta(days=7)}


def _load(session_id: str) -> dict[str, Any]:
    raw = runtime_document_store("monitoring", local_root=MONITORING_STORAGE).read(session_id)
    if raw is None:
        return {"rules": [], "events": []}
    return raw


def _save(session_id: str, payload: dict[str, Any]) -> None:
    runtime_document_store("monitoring", local_root=MONITORING_STORAGE).write(session_id, payload)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_timestamp(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _schedule_state(cadence: str, created_at: str, last_evaluated_at: str | None, now: datetime) -> tuple[bool, str | None]:
    if cadence == "manual":
        return True, None
    interval = CADENCE_INTERVALS.get(cadence)
    if interval is None:
        raise ValueError("Alert cadence must be manual, daily, or weekly.")
    if last_evaluated_at is None:
        return True, created_at
    next_due = _parse_timestamp(last_evaluated_at) + interval
    return now >= next_due, _format_timestamp(next_due)


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == "gt": return value > threshold
    if operator == "gte": return value >= threshold
    if operator == "lt": return value < threshold
    if operator == "lte": return value <= threshold
    if operator == "eq": return value == threshold
    if operator == "neq": return value != threshold
    raise ValueError("Unsupported alert operator.")


def _metric_map(dataset_id: str, session_id: str) -> dict[str, Any]:
    session = require_session(session_id)
    if session.dataset_id != dataset_id:
        raise ValueError("Analysis session does not match the dataset.")
    overview = build_overview(dataset_id, scope=session.scope)
    return {m.id: m for m in overview.metrics}


def list_alerts(dataset_id: str, session_id: str) -> AlertsResponse:
    session = require_session(session_id)
    if session.dataset_id != dataset_id:
        raise ValueError("Analysis session does not match the dataset.")
    summary = get_dataset(dataset_id)
    payload = _load(session_id)
    now = datetime.now(timezone.utc)
    rules = []
    for raw in payload.get("rules", []):
        if raw.get("dataset_id") != dataset_id:
            continue
        due, next_due_at = _schedule_state(raw.get("cadence", "manual"), raw["created_at"], raw.get("last_evaluated_at"), now)
        rules.append(AlertRule.model_validate({**raw, "due": due, "next_due_at": next_due_at}))
    events = [AlertEvent.model_validate(e) for e in payload.get("events", []) if e.get("dataset_id") == dataset_id]
    events.sort(key=lambda e: e.evaluated_at, reverse=True)
    return AlertsResponse(
        dataset_id=dataset_id,
        business_model=summary.business_model if summary else None,
        business_model_label=summary.business_model_label if summary else None,
        scope_label=scope_label(session.scope),
        rules=rules,
        events=events[:50],
    )


def create_rule(dataset_id: str, session_id: str, request: AlertRuleCreate) -> AlertRule:
    session = require_session(session_id)
    if session.dataset_id != dataset_id:
        raise ValueError("Analysis session does not match the dataset.")
    if request.operator not in OPS:
        raise ValueError("Alert operator is not supported.")
    if request.cadence not in SUPPORTED_CADENCES:
        raise ValueError("Alert cadence must be manual, daily, or weekly.")
    metrics = _metric_map(dataset_id, session_id)
    metric = metrics.get(request.metric)
    if metric is None:
        raise ValueError(f"Metric '{request.metric}' is not available in the current dataset.")
    rule_id = uuid.uuid4().hex
    now = _now()
    rule = AlertRule(
        rule_id=rule_id,
        dataset_id=dataset_id,
        session_id=session_id,
        name=request.name.strip() or f"{metric.label} alert",
        metric=request.metric,
        operator=request.operator,
        threshold=float(request.threshold),
        cadence=request.cadence,
        scope_label=scope_label(session.scope),
        active=True,
        created_at=now,
        due=True,
        next_due_at=None if request.cadence == "manual" else now,
    )
    payload = _load(session_id)
    payload.setdefault("rules", []).append(rule.model_dump())
    _save(session_id, payload)
    return rule


def delete_rule(dataset_id: str, session_id: str, rule_id: str) -> None:
    require_session(session_id)
    payload = _load(session_id)
    before = len(payload.get("rules", []))
    payload["rules"] = [r for r in payload.get("rules", []) if not (r.get("rule_id") == rule_id and r.get("dataset_id") == dataset_id)]
    if len(payload["rules"]) == before:
        raise ValueError("Alert rule not found.")
    _save(session_id, payload)


def evaluate_alerts(dataset_id: str, session_id: str) -> AlertsResponse:
    session = require_session(session_id)
    if session.dataset_id != dataset_id:
        raise ValueError("Analysis session does not match the dataset.")
    metrics = _metric_map(dataset_id, session_id)
    payload = _load(session_id)
    now = _now()
    new_events: list[AlertEvent] = []
    for raw in payload.get("rules", []):
        if raw.get("dataset_id") != dataset_id or not raw.get("active", True):
            continue
        metric = metrics.get(raw["metric"])
        raw["last_evaluated_at"] = now
        if metric is None or metric.value is None:
            status = "unavailable"
            title = f"{raw['name']} cannot be evaluated"
            message = "The monitored metric is not available in the current scope, so no alert decision was made."
            value = None
            evidence = Evidence(metric=raw["metric"], value=None, calculation="validated overview metric unavailable", scope=scope_label(session.scope), source_fields=[])
        else:
            value = float(metric.value)
            triggered = _compare(value, raw["operator"], float(raw["threshold"]))
            status = "triggered" if triggered else "clear"
            direction = OPS[raw["operator"]]
            title = f"{raw['name']} is {status}"
            message = f"{metric.label} is {metric.display_value} and {'crosses' if triggered else 'does not cross'} the {direction} {raw['threshold']:g} threshold."
            evidence = metric.evidence.model_copy(update={"scope": scope_label(session.scope)})
        event = AlertEvent(
            event_id=uuid.uuid4().hex,
            rule_id=raw["rule_id"],
            dataset_id=dataset_id,
            session_id=session_id,
            status=status,
            metric=raw["metric"],
            value=value,
            threshold=float(raw["threshold"]),
            operator=raw["operator"],
            title=title,
            message=message,
            scope_label=scope_label(session.scope),
            evidence=evidence,
            evaluated_at=now,
        )
        new_events.append(event)
    payload.setdefault("events", []).extend(e.model_dump() for e in new_events)
    _save(session_id, payload)
    return list_alerts(dataset_id, session_id)
