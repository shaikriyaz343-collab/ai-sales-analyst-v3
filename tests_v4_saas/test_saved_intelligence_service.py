from pathlib import Path

import pytest

from backend.api.services.onboarding import onboard
from backend.api.services.saved_intelligence import list_saved, save_intelligence, delete_saved
from backend.api.services.session import create_session, update_scope, replace_dataset
from backend.api.contracts import SavedIntelligenceCreate, ScopeFilter

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"

def _load(name: str):
    with (SAMPLES / name).open("rb") as fh:
        return onboard(name, fh)

def test_save_and_list_explore_analysis():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    item = save_intelligence(summary.dataset_id, session.session_id, SavedIntelligenceCreate(name="Revenue by product", source_workspace="explore", source_id="revenue:product"))
    result = list_saved(summary.dataset_id, session.session_id)
    assert [x.id for x in result.items] == [item.id]
    assert item.metric == "revenue"
    assert item.dimension == "product"
    assert item.scope_label == "All data"

def test_saved_intelligence_captures_scope_snapshot():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    session = update_scope(session.session_id, [ScopeFilter(field="region", operator="in", values=["North"])])
    item = save_intelligence(summary.dataset_id, session.session_id, SavedIntelligenceCreate(name="North revenue", source_workspace="explore", source_id="revenue:product"))
    assert item.scope_label == "region = North"
    assert item.scope_filters[0].field == "region"

def test_delete_saved_intelligence():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    item = save_intelligence(summary.dataset_id, session.session_id, SavedIntelligenceCreate(name="Revenue by product", source_workspace="explore", source_id="revenue:product"))
    delete_saved(summary.dataset_id, session.session_id, item.id)
    assert list_saved(summary.dataset_id, session.session_id).items == []

def test_save_validates_source_workspace():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    with pytest.raises(ValueError, match="Unsupported saved intelligence source"):
        save_intelligence(summary.dataset_id, session.session_id, SavedIntelligenceCreate(name="Bad", source_workspace="unknown", source_id="x"))

def test_dataset_replacement_invalidates_saved_intelligence():
    retail = _load("retail.csv")
    pipeline = _load("pipeline.csv")
    session = create_session(retail.dataset_id)
    save_intelligence(retail.dataset_id, session.session_id, SavedIntelligenceCreate(name="Revenue by product", source_workspace="explore", source_id="revenue:product"))
    replace_dataset(session.session_id, pipeline.dataset_id)
    assert list_saved(pipeline.dataset_id, session.session_id).items == []


def test_save_insight_uses_validated_source():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    from backend.api.services.insights import build_insights
    insights = build_insights(summary.dataset_id, scope=session.scope)
    if not insights.insights:
        pytest.skip("Retail fixture has no validated insight")
    source = insights.insights[0]
    item = save_intelligence(summary.dataset_id, session.session_id, SavedIntelligenceCreate(name="Saved insight", source_workspace="insights", source_id=source.id))
    assert item.kind == "insight"
    assert item.source_id == source.id
    assert item.evidence.metric == source.evidence.metric


def test_save_action_uses_validated_source():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    from backend.api.services.actions import build_actions
    actions = build_actions(summary.dataset_id, scope=session.scope)
    if not actions.actions:
        pytest.skip("Retail fixture has no validated action")
    source = actions.actions[0]
    item = save_intelligence(summary.dataset_id, session.session_id, SavedIntelligenceCreate(name="Saved action", source_workspace="actions", source_id=source.id))
    assert item.kind == "action"
    assert item.source_id == source.id
    assert item.evidence.metric == source.evidence.metric
