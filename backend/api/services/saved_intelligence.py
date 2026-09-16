from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..contracts import Evidence, SavedIntelligence, SavedIntelligenceCreate, SavedIntelligenceResponse
from ..runtime_persistence import runtime_document_store
from .actions import build_actions
from .explore import build_explore
from .insights import build_insights
from .onboarding import STORAGE, get_dataset
from .session import require_session, scope_label
from .overview import build_overview

SAVED_STORAGE = STORAGE.parent / "runtime_saved_intelligence"


def _load(session_id: str) -> list[dict[str, Any]]:
    raw = runtime_document_store("saved_intelligence", local_root=SAVED_STORAGE).read(session_id)
    if raw is None:
        return []
    return raw


def _save(session_id: str, items: list[dict[str, Any]]) -> None:
    runtime_document_store("saved_intelligence", local_root=SAVED_STORAGE).write(session_id, items)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_context(dataset_id: str, session_id: str):
    session = require_session(session_id)
    if session.dataset_id != dataset_id:
        raise ValueError("Analysis session does not match the dataset.")
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")
    return session, summary


def _from_source(dataset_id: str, session_id: str, request: SavedIntelligenceCreate) -> dict[str, Any]:
    session, summary = _validate_context(dataset_id, session_id)
    if request.source_workspace == "explore":
        if not request.metric or not request.dimension:
            raise ValueError("Explore saves require a metric and dimension.")
        result = build_explore(dataset_id, request.metric, request.dimension, 8, scope=session.scope)
        evidence = Evidence(
            metric=result.metric,
            value=result.total_value,
            comparison_value=None,
            calculation=f"Total {result.metric_label.lower()} for the selected scope.",
            scope=result.scope_label,
            source_fields=sorted({field for row in result.rows for field in row.evidence.get("source_fields", [])}),
            source_records=sorted({record for row in result.rows for record in row.evidence.get("source_records", [])})[:12],
        )
        title = request.title.strip() or f"{result.metric_label} by {result.dimension_label}"
        summary_text = request.summary.strip() or f"Explore {result.metric_label.lower()} by {result.dimension_label.lower()} for the current scope."
        return {
            "kind": "explore",
            "title": title,
            "summary": summary_text,
            "metric": result.metric,
            "metric_label": result.metric_label,
            "dimension": result.dimension,
            "dimension_label": result.dimension_label,
            "value": result.total_value,
            "display_value": result.total_display_value,
            "evidence": evidence.model_dump(),
            "source_id": f"{result.metric}:{result.dimension}",
        }

    if request.source_workspace == "insights":
        result = build_insights(dataset_id, scope=session.scope)
        item = next((x for x in result.insights if x.id == request.source_id), None)
        if item is None:
            raise ValueError("Insight is no longer available in the current scope.")
        metric_label = item.metric
        try:
            metric_label = next((m.label for m in build_overview(dataset_id, scope=session.scope).metrics if m.id == item.metric), item.metric)
        except Exception:
            pass
        return {
            "kind": "insight",
            "title": request.title.strip() or item.title,
            "summary": request.summary.strip() or item.what_changed,
            "metric": item.metric,
            "metric_label": metric_label,
            "dimension": None,
            "dimension_label": None,
            "value": item.value,
            "display_value": item.display_value,
            "evidence": item.evidence.model_dump(),
            "source_id": item.id,
        }

    if request.source_workspace == "actions":
        result = build_actions(dataset_id, scope=session.scope)
        item = next((x for x in result.actions if x.id == request.source_id), None)
        if item is None:
            raise ValueError("Action is no longer available in the current scope.")
        metric_label = item.metric
        try:
            metric_label = next((m.label for m in build_overview(dataset_id, scope=session.scope).metrics if m.id == item.metric), item.metric)
        except Exception:
            pass
        return {
            "kind": "action",
            "title": request.title.strip() or item.title,
            "summary": request.summary.strip() or item.action,
            "metric": item.metric,
            "metric_label": metric_label,
            "dimension": None,
            "dimension_label": None,
            "value": None,
            "display_value": item.display_value,
            "evidence": item.evidence.model_dump(),
            "source_id": item.id,
        }

    raise ValueError("Unsupported saved intelligence source.")


def _refresh_source(dataset_id: str, session_id: str, item: dict[str, Any]) -> dict[str, Any] | None:
    """Recalculate a saved item from the current validated dataset and scope."""
    session, _ = _validate_context(dataset_id, session_id)
    workspace = item.get("source_workspace")
    source_id = str(item.get("source_id") or "")

    if workspace == "explore":
        metric = item.get("metric")
        dimension = item.get("dimension")
        if not metric or not dimension:
            return None
        result = build_explore(dataset_id, str(metric), str(dimension), 8, scope=session.scope)
        evidence = Evidence(
            metric=result.metric,
            value=result.total_value,
            comparison_value=None,
            calculation=f"Total {result.metric_label.lower()} for the selected scope.",
            scope=result.scope_label,
            source_fields=sorted({field for row in result.rows for field in row.evidence.get("source_fields", [])}),
            source_records=sorted({record for row in result.rows for record in row.evidence.get("source_records", [])})[:12],
        )
        return {"value": result.total_value, "display_value": result.total_display_value, "evidence": evidence.model_dump()}

    if workspace == "insights":
        result = build_insights(dataset_id, scope=session.scope)
        current = next((x for x in result.insights if x.id == source_id), None)
        if current is None:
            return None
        return {"value": current.value, "display_value": current.display_value, "evidence": current.evidence.model_dump()}

    if workspace == "actions":
        result = build_actions(dataset_id, scope=session.scope, session_id=session_id)
        current = next((x for x in result.actions if x.id == source_id), None)
        if current is None:
            return None
        return {"value": current.evidence.value, "display_value": current.display_value, "evidence": current.evidence.model_dump()}

    return None


def _refresh_items(dataset_id: str, session_id: str) -> list[dict[str, Any]]:
    """Refresh active saved intelligence before it is returned to the workspace."""
    items = _load(session_id)
    changed = False
    now = _now()
    for item in items:
        if item.get("dataset_id") != dataset_id or not item.get("active", True):
            continue
        try:
            refreshed = _refresh_source(dataset_id, session_id, item)
        except (ValueError, KeyError, TypeError):
            refreshed = None
        if refreshed is None:
            continue
        for key in ("value", "display_value", "evidence"):
            if item.get(key) != refreshed.get(key):
                item[key] = refreshed[key]
                changed = True
        item["scope_label"] = scope_label(require_session(session_id).scope)
        item["scope_filters"] = require_session(session_id).scope.filters
        item["updated_at"] = now
        changed = True
    if changed:
        _save(session_id, items)
    return items


def list_saved(dataset_id: str, session_id: str) -> SavedIntelligenceResponse:
    session, summary = _validate_context(dataset_id, session_id)
    refreshed_items = _refresh_items(dataset_id, session_id)
    items = [SavedIntelligence.model_validate(item) for item in refreshed_items if item.get("dataset_id") == dataset_id and item.get("active", True)]
    items.sort(key=lambda item: item.updated_at, reverse=True)
    return SavedIntelligenceResponse(
        dataset_id=dataset_id,
        business_model=summary.business_model,
        business_model_label=summary.business_model_label,
        scope_label=scope_label(session.scope),
        items=items,
    )


def save_intelligence(dataset_id: str, session_id: str, request: SavedIntelligenceCreate) -> SavedIntelligence:
    session, _ = _validate_context(dataset_id, session_id)
    if not request.name.strip():
        raise ValueError("Saved intelligence needs a name.")
    if request.source_workspace == "explore" and request.source_id and ":" in request.source_id:
        metric, dimension = request.source_id.split(":", 1)
        request = request.model_copy(update={"metric": metric, "dimension": dimension})
    source = _from_source(dataset_id, session_id, request)
    now = _now()
    item = SavedIntelligence(
        id=uuid.uuid4().hex,
        dataset_id=dataset_id,
        session_id=session_id,
        name=request.name.strip(),
        kind=source["kind"],
        title=source["title"],
        summary=source["summary"],
        metric=source["metric"],
        metric_label=source["metric_label"],
        dimension=source["dimension"],
        dimension_label=source["dimension_label"],
        value=source["value"],
        display_value=source["display_value"],
        scope_label=scope_label(session.scope),
        scope_filters=session.scope.filters,
        evidence=Evidence.model_validate(source["evidence"]),
        source_workspace=request.source_workspace,
        source_id=source["source_id"],
        active=True,
        created_at=now,
        updated_at=now,
    )
    items = _load(session_id)
    items.append(item.model_dump())
    _save(session_id, items)
    return item


def delete_saved(dataset_id: str, session_id: str, item_id: str) -> None:
    _validate_context(dataset_id, session_id)
    items = _load(session_id)
    filtered = [item for item in items if not (item.get("id") == item_id and item.get("dataset_id") == dataset_id)]
    if len(filtered) == len(items):
        raise ValueError("Saved intelligence item not found.")
    _save(session_id, filtered)


def invalidate_for_dataset_replacement(session_id: str) -> None:
    store = runtime_document_store("saved_intelligence", local_root=SAVED_STORAGE)
    if not store.exists(session_id):
        return
    items = _load(session_id)
    if not items:
        return
    # Keep the historical file but deactivate items so a later productized workspace
    # can offer history without ever surfacing stale intelligence as current truth.
    for item in items:
        item["active"] = False
        item["updated_at"] = _now()
    _save(session_id, items)
