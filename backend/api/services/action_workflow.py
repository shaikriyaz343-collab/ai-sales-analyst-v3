from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..config import settings
from ..runtime_persistence import runtime_document_store
from .actions import build_actions
from .onboarding import STORAGE, get_dataset
from .session import require_session

_ACTION_STATUSES = {"open", "in_progress", "done", "blocked"}
_ACTION_STORAGE = STORAGE.parent / "runtime_action_workflow"


def _load(session_id: str) -> dict[str, dict[str, Any]]:
    raw = runtime_document_store("action_workflow", local_root=_ACTION_STORAGE).read(session_id)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("Stored action workflow state is invalid.")
    return raw


def _save(session_id: str, state: dict[str, dict[str, Any]]) -> None:
    runtime_document_store("action_workflow", local_root=_ACTION_STORAGE).write(session_id, state)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_context(dataset_id: str, session_id: str):
    session = require_session(session_id)
    if session.dataset_id != dataset_id:
        raise ValueError("Analysis session does not match the dataset.")
    if get_dataset(dataset_id) is None:
        raise ValueError("Dataset not found.")
    return session


def get_action(dataset_id: str, session_id: str, action_id: str):
    session = _validate_context(dataset_id, session_id)
    actions = build_actions(dataset_id, scope=session.scope, session_id=session_id)
    return next((item for item in actions.actions if item.id == action_id), None)


def update_action_status(dataset_id: str, session_id: str, action_id: str, status: str):
    session = _validate_context(dataset_id, session_id)
    normalized = status.strip().lower()
    if normalized not in _ACTION_STATUSES:
        raise ValueError("Unsupported action status.")

    actions = build_actions(dataset_id, scope=session.scope, session_id=session_id)
    current = next((item for item in actions.actions if item.id == action_id), None)
    if current is None:
        raise ValueError("Action is no longer available in the current scope.")

    state = _load(session_id)
    state[action_id] = {"status": normalized, "updated_at": _now()}
    _save(session_id, state)
    current.status = normalized
    return current


def status_for(session_id: str, action_id: str) -> str:
    return str(_load(session_id).get(action_id, {}).get("status") or "open")


def is_valid_status(status: str) -> bool:
    return status in _ACTION_STATUSES
