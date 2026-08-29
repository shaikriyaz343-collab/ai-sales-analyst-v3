from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..contracts import AlertEvent, AlertRule, AlertsResponse, AlertRuleCreate, Evidence
from .onboarding import get_dataset, STORAGE
from .overview import build_overview
from .session import get_session, require_session, scope_label

MONITORING_STORAGE = STORAGE.parent / "runtime_monitoring"
OPS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "eq": "=", "neq": "≠"}


def _path(session_id: str) -> Path:
    MONITORING_STORAGE.mkdir(parents=True, exist_ok=True)
    return MONITORING_STORAGE / f"{session_id}.json"


def _load(session_id: str) -> dict[str, Any]:
    path = _path(session_id)
    if not path.exists():
        return {"rules": [], "events": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(session_id: str, payload: dict[str, Any]) -> None:
    _path(session_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    rules = [AlertRule.model_validate(r) for r in payload.get("rules", []) if r.get("dataset_id") == dataset_id]
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
    if request.cadence not in {"manual", "daily", "weekly"}:
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
