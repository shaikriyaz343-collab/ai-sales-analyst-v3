from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.api.contracts import AlertRuleCreate, ScopeFilter
from backend.api.services.onboarding import onboard
from backend.api.services.session import create_session, replace_dataset, update_scope
from backend.api.services.monitoring import _load as monitoring_state_load, _schedule_state, create_rule, delete_rule, evaluate_alerts, list_alerts

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def _load(name: str):
    with (SAMPLES / name).open("rb") as fh:
        return onboard(name, fh)


def test_create_rule_validates_against_current_metrics():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    rule = create_rule(summary.dataset_id, session.session_id, AlertRuleCreate(name="Returns watch", metric="return_rate", operator="gt", threshold=10))
    assert rule.metric == "return_rate"
    assert rule.scope_label == "All data"
    assert rule.cadence == "manual"


def test_rule_rejects_unsupported_metric_and_operator():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    with pytest.raises(ValueError, match="not available"):
        create_rule(summary.dataset_id, session.session_id, AlertRuleCreate(metric="churn", operator="gt", threshold=10))
    with pytest.raises(ValueError, match="operator"):
        create_rule(summary.dataset_id, session.session_id, AlertRuleCreate(metric="revenue", operator="wat", threshold=10))


def test_cadence_contract_allows_only_manual_daily_weekly():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    for cadence in ("manual", "daily", "weekly"):
        rule = create_rule(summary.dataset_id, session.session_id, AlertRuleCreate(name=f"{cadence} watch", metric="revenue", operator="gt", threshold=0, cadence=cadence))
        assert rule.cadence == cadence
    with pytest.raises(ValueError, match="cadence"):
        create_rule(summary.dataset_id, session.session_id, AlertRuleCreate(metric="revenue", operator="gt", threshold=0, cadence="hourly"))


def test_schedule_state_marks_manual_always_due():
    now = datetime(2026, 9, 16, tzinfo=timezone.utc)
    due, next_due = _schedule_state("manual", "2026-09-01T00:00:00Z", "2026-09-15T00:00:00Z", now)
    assert due is True
    assert next_due is None


def test_schedule_state_marks_daily_due_after_one_day():
    last = "2026-09-15T10:00:00Z"
    before = datetime(2026, 9, 16, 9, 59, 59, tzinfo=timezone.utc)
    at_due = datetime(2026, 9, 16, 10, 0, 0, tzinfo=timezone.utc)
    due_before, next_before = _schedule_state("daily", "2026-09-01T00:00:00Z", last, before)
    due_at, next_at = _schedule_state("daily", "2026-09-01T00:00:00Z", last, at_due)
    assert due_before is False
    assert next_before == "2026-09-16T10:00:00Z"
    assert due_at is True
    assert next_at == "2026-09-16T10:00:00Z"


def test_schedule_state_uses_seven_day_weekly_interval():
    last = "2026-09-09T08:30:00Z"
    due, next_due = _schedule_state("weekly", "2026-09-01T00:00:00Z", last, datetime(2026, 9, 16, 8, 30, tzinfo=timezone.utc))
    assert due is True
    assert next_due == "2026-09-16T08:30:00Z"


def test_schedule_state_first_scheduled_run_is_immediately_due():
    now = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)
    due, next_due = _schedule_state("daily", "2026-09-16T11:30:00Z", None, now)
    assert due is True
    assert next_due == "2026-09-16T11:30:00Z"


def test_evaluation_triggers_using_same_scope_and_metric_evidence():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    update_scope(session.session_id, [ScopeFilter(field="region", operator="in", values=["North"])])
    rule = create_rule(summary.dataset_id, session.session_id, AlertRuleCreate(name="North return watch", metric="return_rate", operator="gt", threshold=10))
    result = evaluate_alerts(summary.dataset_id, session.session_id)
    event = next(e for e in result.events if e.rule_id == rule.rule_id)
    assert result.scope_label == "region = North"
    assert event.scope_label == "region = North"
    assert event.evidence.scope == "region = North"
    assert event.status in {"triggered", "clear", "unavailable"}


@pytest.mark.parametrize("name,metric,threshold", [
    ("Pipeline watch", "pipeline_value", 1000),
    ("MRR watch", "mrr", 1000),
    ("Billings watch", "billings", 1000),
])
def test_create_rule_supports_metrics_across_business_models(name, metric, threshold):
    sample = {"Pipeline watch": "pipeline.csv", "MRR watch": "subscription.csv", "Billings watch": "services.csv"}[name]
    summary = _load(sample)
    session = create_session(summary.dataset_id)
    rule = create_rule(summary.dataset_id, session.session_id, AlertRuleCreate(name=name, metric=metric, operator="gt", threshold=threshold))
    assert rule.metric == metric


def test_evaluation_clears_when_threshold_is_not_met():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    rule = create_rule(summary.dataset_id, session.session_id, AlertRuleCreate(name="High revenue watch", metric="revenue", operator="gt", threshold=999999999))
    result = evaluate_alerts(summary.dataset_id, session.session_id)
    event = next(e for e in result.events if e.rule_id == rule.rule_id)
    assert event.status == "clear"


def test_delete_rule_removes_monitor():
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    rule = create_rule(summary.dataset_id, session.session_id, AlertRuleCreate(metric="revenue", operator="gt", threshold=0))
    delete_rule(summary.dataset_id, session.session_id, rule.rule_id)
    assert all(r.rule_id != rule.rule_id for r in list_alerts(summary.dataset_id, session.session_id).rules)


def test_dataset_replacement_clears_prior_monitoring_state():
    retail = _load("retail.csv")
    pipeline = _load("pipeline.csv")
    session = create_session(retail.dataset_id)
    create_rule(retail.dataset_id, session.session_id, AlertRuleCreate(metric="revenue", operator="gt", threshold=0))
    replaced = replace_dataset(session.session_id, pipeline.dataset_id)
    assert replaced.dataset_id == pipeline.dataset_id
    assert list_alerts(pipeline.dataset_id, session.session_id).rules == []
    assert monitoring_state_load(session.session_id)["rules"] == []
