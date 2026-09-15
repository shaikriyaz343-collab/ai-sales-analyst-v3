from types import SimpleNamespace

import pytest

from backend.api.contracts import ActionItem, Evidence, ActionsResponse
from backend.api.services import action_workflow


def _action(action_id: str = "action-risk-1", status: str = "open") -> ActionItem:
    return ActionItem(
        id=action_id,
        priority="high",
        status=status,
        title="Follow up",
        action="Review the signal.",
        owner="Sales Leadership",
        rationale="Validated reason",
        expected_outcome="Address the signal.",
        metric="pipeline_value",
        display_value="$100K",
        evidence=Evidence(
            metric="pipeline_value",
            value=100000,
            calculation="validated",
            source_fields=["amount"],
        ),
        source_insight_id="risk-1",
    )


def _context(monkeypatch, actions: list[ActionItem]):
    session = SimpleNamespace(dataset_id="d1", scope=SimpleNamespace())
    monkeypatch.setattr(action_workflow, "require_session", lambda session_id: session)
    monkeypatch.setattr(action_workflow, "get_dataset", lambda dataset_id: object())
    monkeypatch.setattr(
        action_workflow,
        "build_actions",
        lambda dataset_id, scope=None, session_id=None: ActionsResponse(
            dataset_id=dataset_id,
            business_model="sales_pipeline",
            business_model_label="Sales pipeline",
            headline="headline",
            summary="summary",
            actions=actions,
        ),
    )
    return session


def test_update_action_status_persists_and_returns_updated_action(monkeypatch) -> None:
    actions = [_action()]
    stored: dict[str, dict[str, str]] = {}
    _context(monkeypatch, actions)
    monkeypatch.setattr(action_workflow, "_load", lambda session_id: dict(stored))
    monkeypatch.setattr(action_workflow, "_save", lambda session_id, state: stored.update(state))
    monkeypatch.setattr(action_workflow, "_now", lambda: "2026-09-15T12:00:00Z")

    updated = action_workflow.update_action_status("d1", "s1", "action-risk-1", "in_progress")

    assert updated.status == "in_progress"
    assert stored["action-risk-1"]["status"] == "in_progress"
    assert stored["action-risk-1"]["updated_at"] == "2026-09-15T12:00:00Z"
    assert action_workflow.is_valid_status("blocked") is True


def test_update_action_status_rejects_unknown_status(monkeypatch) -> None:
    _context(monkeypatch, [_action()])

    with pytest.raises(ValueError, match="Unsupported action status"):
        action_workflow.update_action_status("d1", "s1", "action-risk-1", "cancelled")


def test_update_action_status_rejects_action_outside_current_scope(monkeypatch) -> None:
    _context(monkeypatch, [])

    with pytest.raises(ValueError, match="no longer available"):
        action_workflow.update_action_status("d1", "s1", "action-risk-1", "done")
