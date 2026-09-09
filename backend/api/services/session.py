from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ..config import settings
from ..contracts import AnalysisSession, ScopeFilter, ScopeState
from ..runtime_persistence import runtime_document_store, runtime_object_store
from .onboarding import STORAGE, get_dataset
from schema_profiler_v2 import load_dataframe, profile_dataframe
from semantic_business_model_v2 import build_semantic_model

SESSION_STORAGE = STORAGE.parent / "runtime_sessions"


def _session_path(session_id: str) -> Path:
    return SESSION_STORAGE / f"{session_id}.json"


def _canonical_fields(dataset_id: str) -> set[str]:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")
    suffix = Path(summary.file_name).suffix.lower()
    path = runtime_object_store(local_root=STORAGE).path_for(f"{dataset_id}{suffix}")
    if not path.exists():
        raise ValueError("Dataset file is no longer available for analysis.")
    data = load_dataframe(path)
    profile = profile_dataframe(data)
    semantic = build_semantic_model(profile, data=data)
    concepts = set(str(x) for x in semantic.get("available_concepts", []))
    return {str(x) for x in data.columns} | concepts


def create_session(dataset_id: str, organization_id: str | None = None, workspace_id: str | None = None) -> AnalysisSession:
    summary = get_dataset(dataset_id, organization_id=organization_id, workspace_id=workspace_id)
    if summary is None:
        raise ValueError("Dataset not found.")
    organization_id = organization_id or summary.organization_id
    workspace_id = workspace_id or summary.workspace_id
    session_id = uuid.uuid4().hex
    session = AnalysisSession(session_id=session_id, dataset_id=dataset_id, organization_id=organization_id, workspace_id=workspace_id, scope=ScopeState())
    runtime_document_store("sessions", local_root=SESSION_STORAGE).write(session_id, session.model_dump())
    return session


def get_session(session_id: str) -> AnalysisSession | None:
    raw = runtime_document_store("sessions", local_root=SESSION_STORAGE).read(session_id)
    if raw is None:
        return None
    return AnalysisSession.model_validate(raw)


def require_session(session_id: str, organization_id: str | None = None, workspace_id: str | None = None) -> AnalysisSession:
    session = get_session(session_id)
    if session is None:
        raise ValueError("Analysis session not found.")
    if organization_id is not None and session.organization_id != organization_id:
        raise ValueError("Analysis session is not available to this organization.")
    if workspace_id is not None and session.workspace_id != workspace_id:
        raise ValueError("Analysis session is not available to this workspace.")
    if get_dataset(session.dataset_id, organization_id=organization_id, workspace_id=workspace_id) is None:
        raise ValueError("Dataset not found.")
    return session


def replace_dataset(session_id: str, dataset_id: str) -> AnalysisSession:
    session = require_session(session_id)
    if get_dataset(dataset_id) is None:
        raise ValueError("Dataset not found.")
    # Replacing a dataset invalidates all analytical state and scope.
    session.dataset_id = dataset_id
    session.scope = ScopeState()
    session.active_analysis = None
    session.comparison = None
    # Dataset replacement invalidates monitoring rules/events tied to the prior dataset.
    runtime_document_store("monitoring", local_root=STORAGE.parent / "runtime_monitoring").delete(session_id)
    from .saved_intelligence import invalidate_for_dataset_replacement
    invalidate_for_dataset_replacement(session_id)
    runtime_document_store("sessions", local_root=SESSION_STORAGE).write(session_id, session.model_dump())
    return session


def update_scope(session_id: str, filters: list[ScopeFilter]) -> AnalysisSession:
    session = require_session(session_id)
    valid_fields = _canonical_fields(session.dataset_id)
    for item in filters:
        if item.field not in valid_fields:
            raise ValueError(f"Scope field '{item.field}' is not available in this dataset.")
        if item.operator not in {"in", "not_in", "eq", "neq"}:
            raise ValueError(f"Scope operator '{item.operator}' is not supported.")
        if not item.values:
            raise ValueError(f"Scope filter for '{item.field}' must contain at least one value.")
    session.scope = ScopeState(filters=filters)
    runtime_document_store("sessions", local_root=SESSION_STORAGE).write(session_id, session.model_dump())
    return session


def scope_values(session_id: str, field: str, limit: int = 100) -> list[str]:
    session = require_session(session_id)
    valid_fields = _canonical_fields(session.dataset_id)
    if field not in valid_fields:
        raise ValueError(f"Scope field '{field}' is not available in this dataset.")
    summary = get_dataset(session.dataset_id)
    suffix = Path(summary.file_name).suffix.lower()
    path = runtime_object_store(local_root=STORAGE).path_for(f"{session.dataset_id}{suffix}")
    data = load_dataframe(path)
    profile = profile_dataframe(data)
    canonical = build_semantic_model(profile, data=data)
    # Prefer the canonical semantic field where available, otherwise raw column.
    source = data[field] if field in data.columns else None
    if source is None:
        recognized = profile.get("recognized", {}).get(field, [])
        source = data[recognized[0]] if recognized and recognized[0] in data.columns else None
    if source is None:
        raise ValueError(f"Scope field '{field}' is not available as a filterable column.")
    values = []
    seen = set()
    for raw in source.dropna().tolist():
        value = str(raw)
        if value not in seen:
            seen.add(value); values.append(value)
        if len(values) >= max(1, min(int(limit), 500)):
            break
    return sorted(values)


def reset_scope(session_id: str) -> AnalysisSession:
    session = require_session(session_id)
    session.scope = ScopeState()
    runtime_document_store("sessions", local_root=SESSION_STORAGE).write(session_id, session.model_dump())
    return session


def apply_scope(data, scope: ScopeState):
    if not scope.filters:
        return data
    result = data.copy()
    for item in scope.filters:
        if item.field not in result.columns:
            raise ValueError(f"Scope field '{item.field}' is not available in the analyzed data.")
        series = result[item.field].astype(str)
        values = {str(v) for v in item.values}
        if item.operator == "in":
            mask = series.isin(values)
        elif item.operator == "not_in":
            mask = ~series.isin(values)
        elif item.operator == "eq":
            mask = series == str(item.values[0])
        else:
            mask = series != str(item.values[0])
        result = result.loc[mask]
    return result


def scope_label(scope: ScopeState) -> str:
    if not scope.filters:
        return "All data"
    parts: list[str] = []
    for item in scope.filters:
        if len(item.values) == 1:
            parts.append(f"{item.field} = {item.values[0]}")
        else:
            parts.append(f"{item.field} in ({', '.join(str(v) for v in item.values)})")
    return " · ".join(parts)
