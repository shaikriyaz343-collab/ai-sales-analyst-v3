from io import BytesIO
from pathlib import Path

import pytest
import pandas as pd

from backend.api.contracts import ScopeFilter
from backend.api.services.onboarding import onboard
from backend.api.services.session import create_session, get_session, update_scope, reset_scope, replace_dataset, apply_scope, scope_values
from backend.api.services.overview import build_overview
from backend.api.services.explore import build_explore
from backend.api.services.insights import build_insights
from backend.api.services.actions import build_actions
from backend.api.services.ask import answer_question

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"

def _upload(name: str):
    with (SAMPLES / name).open("rb") as fh:
        return onboard(name, fh)

def test_session_starts_with_clean_all_data_scope():
    summary = _upload("retail.csv")
    session = create_session(summary.dataset_id)
    assert session.dataset_id == summary.dataset_id
    assert session.scope.filters == []

def test_scope_filters_change_overview_explore_and_evidence():
    summary = _upload("retail.csv")
    session = create_session(summary.dataset_id)
    session = update_scope(session.session_id, [ScopeFilter(field="region", operator="in", values=["North"])])
    overview = build_overview(summary.dataset_id, scope=session.scope)
    explore = build_explore(summary.dataset_id, "revenue", "region", scope=session.scope)
    assert session.scope.filters[0].values == ["North"]
    assert overview.scope_label == "region = North"
    assert overview.metrics[0].evidence.scope == "region = North"
    assert explore.scope_label == "region = North"
    assert explore.total_value == pytest.approx(2800.0)
    assert explore.rows[0].evidence["scope"] == "region = North"

def test_scope_is_used_by_insights_actions_and_ask():
    summary = _upload("retail.csv")
    session = create_session(summary.dataset_id)
    session = update_scope(session.session_id, [ScopeFilter(field="product", operator="in", values=["Phone"])])
    insights = build_insights(summary.dataset_id, scope=session.scope)
    actions = build_actions(summary.dataset_id, scope=session.scope)
    answer = answer_question(summary.dataset_id, "What is total revenue?", scope=session.scope)
    assert insights.scope_label == "product = Phone"
    assert all(i.evidence.scope == "product = Phone" for i in insights.insights)
    assert all(a.evidence.scope == "product = Phone" for a in actions.actions)
    assert answer.answer.evidence is not None
    assert answer.answer.evidence.scope == "product = Phone"

def test_scope_reset_returns_to_all_data():
    summary = _upload("retail.csv")
    session = create_session(summary.dataset_id)
    session = update_scope(session.session_id, [ScopeFilter(field="region", operator="in", values=["North"])])
    session = reset_scope(session.session_id)
    assert get_session(session.session_id).scope.filters == []
    assert apply_scope(pd.DataFrame({"region":["North","West"]}), session.scope).shape[0] == 2

def test_scope_rejects_unknown_field():
    summary = _upload("retail.csv")
    session = create_session(summary.dataset_id)
    with pytest.raises(ValueError, match="not available"):
        update_scope(session.session_id, [ScopeFilter(field="not_a_field", operator="in", values=["x"])])

def test_scope_values_are_deterministic():
    summary = _upload("retail.csv")
    session = create_session(summary.dataset_id)
    assert scope_values(session.session_id, "region") == sorted({"North", "West", "South", "East"})


def test_dataset_replacement_resets_scope_and_analysis_context():
    retail = _upload("retail.csv")
    pipeline = _upload("pipeline.csv")
    session = create_session(retail.dataset_id)
    session = update_scope(session.session_id, [ScopeFilter(field="region", operator="in", values=["North"])])
    session.active_analysis = {"metric": "revenue", "dimension": "region"}
    from backend.api.services.session import _session_path
    _session_path(session.session_id).write_text(session.model_dump_json(), encoding="utf-8")
    replaced = replace_dataset(session.session_id, pipeline.dataset_id)
    assert replaced.dataset_id == pipeline.dataset_id
    assert replaced.scope.filters == []
    assert replaced.active_analysis is None
    assert replaced.comparison is None
