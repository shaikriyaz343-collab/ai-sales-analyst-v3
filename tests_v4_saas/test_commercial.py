from datetime import datetime, timedelta, timezone

import pytest

from backend.api.services.commercial import (
    SubscriptionSnapshot,
    UsageSnapshot,
    build_entitlements,
    get_plan,
    plan_catalog,
)
from backend.api.services.commercial_store import CommercialRepository


NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


class MemoryStore:
    def __init__(self) -> None:
        self.items = {}

    def read(self, key):
        return self.items.get(key)

    def write(self, key, value):
        self.items[key] = value


def test_catalog_has_trial_and_two_paid_plans() -> None:
    plans = {plan.plan_id: plan for plan in plan_catalog()}

    assert set(plans) == {"trial", "starter", "growth"}
    assert plans["trial"].trial_days == 14
    assert plans["starter"].price_usd_monthly == 49
    assert plans["growth"].price_usd_monthly == 149


def test_unknown_plan_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown commercial plan"):
        get_plan("enterprise")


def test_active_trial_exposes_features_and_remaining_usage() -> None:
    subscription = SubscriptionSnapshot(
        organization_id="org-1",
        plan_id="trial",
        status="trialing",
        trial_started_at=NOW - timedelta(days=2),
        trial_ends_at=NOW + timedelta(days=12),
    )
    usage = UsageSnapshot(
        counts={
            "dataset_uploads": 1,
            "analyst_questions": 7,
            "reports": 0,
            "monitoring_rules": 2,
            "saved_intelligence": 4,
        }
    )

    entitlements = build_entitlements(subscription, usage, now=NOW)

    assert entitlements.access_active is True
    assert entitlements.access_reason == "trial_active"
    assert entitlements.allows_feature("forecast") is True
    assert entitlements.remaining["dataset_uploads"] == 2
    assert entitlements.remaining["analyst_questions"] == 43
    assert entitlements.allows_usage("dataset_uploads", additional=2) is True
    assert entitlements.allows_usage("dataset_uploads", additional=3) is False


def test_expired_trial_has_no_access() -> None:
    subscription = SubscriptionSnapshot(
        organization_id="org-1",
        plan_id="trial",
        status="trialing",
        trial_started_at=NOW - timedelta(days=15),
        trial_ends_at=NOW - timedelta(days=1),
    )
    usage = UsageSnapshot(counts={"dataset_uploads": 1})

    entitlements = build_entitlements(subscription, usage, now=NOW)

    assert entitlements.access_active is False
    assert entitlements.access_reason == "trial_expired"
    assert entitlements.plan_id is None
    assert entitlements.allows_feature("overview") is False
    assert entitlements.allows_usage("dataset_uploads") is False


def test_active_paid_subscription_respects_quota() -> None:
    subscription = SubscriptionSnapshot(
        organization_id="org-1",
        plan_id="starter",
        status="active",
        current_period_start=NOW - timedelta(days=4),
        current_period_end=NOW + timedelta(days=26),
    )
    usage = UsageSnapshot(
        counts={
            "dataset_uploads": 25,
            "analyst_questions": 499,
            "reports": 50,
            "monitoring_rules": 10,
            "saved_intelligence": 100,
        }
    )

    entitlements = build_entitlements(subscription, usage, now=NOW)

    assert entitlements.access_active is True
    assert entitlements.plan_id == "starter"
    assert entitlements.remaining["dataset_uploads"] == 0
    assert entitlements.remaining["analyst_questions"] == 1
    assert entitlements.allows_usage("analyst_questions", additional=1) is True
    assert entitlements.allows_usage("analyst_questions", additional=2) is False


def test_past_due_subscription_keeps_access_with_payment_recovery_state() -> None:
    subscription = SubscriptionSnapshot(
        organization_id="org-1",
        plan_id="growth",
        status="past_due",
        current_period_start=NOW - timedelta(days=10),
        current_period_end=NOW + timedelta(days=20),
    )
    usage = UsageSnapshot(counts={})

    entitlements = build_entitlements(subscription, usage, now=NOW)

    assert entitlements.access_active is True
    assert entitlements.access_reason == "past_due"
    assert entitlements.plan_id == "growth"
    assert entitlements.max_seats == 15


def test_canceled_subscription_is_inactive() -> None:
    subscription = SubscriptionSnapshot(
        organization_id="org-1",
        plan_id="growth",
        status="canceled",
        current_period_start=NOW - timedelta(days=10),
        current_period_end=NOW + timedelta(days=20),
    )
    usage = UsageSnapshot(counts={})

    entitlements = build_entitlements(subscription, usage, now=NOW)

    assert entitlements.access_active is False
    assert entitlements.access_reason == "canceled"
    assert entitlements.plan_id is None
    assert entitlements.max_workspaces == 0


def test_negative_usage_and_negative_increment_do_not_grant_capacity() -> None:
    subscription = SubscriptionSnapshot(
        organization_id="org-1",
        plan_id="starter",
        status="active",
        current_period_end=NOW + timedelta(days=20),
    )
    usage = UsageSnapshot(counts={"dataset_uploads": -20})

    entitlements = build_entitlements(subscription, usage, now=NOW)

    assert entitlements.usage.used("dataset_uploads") == 0
    assert entitlements.remaining["dataset_uploads"] == 25
    assert entitlements.allows_usage("dataset_uploads", additional=-1) is False

def test_usage_consumption_enforces_trial_limit() -> None:
    repo = CommercialRepository(MemoryStore())

    for _ in range(3):
        result = repo.consume_usage(
            "org-1",
            "dataset_uploads",
            now=NOW,
        )
        assert result.allowed is True

    blocked = repo.consume_usage(
        "org-1",
        "dataset_uploads",
        now=NOW,
    )
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.usage.used("dataset_uploads") == 3


def test_usage_consumption_rejects_expired_trial() -> None:
    store = MemoryStore()
    repo = CommercialRepository(store)
    repo.save_subscription(
        SubscriptionSnapshot(
            organization_id="org-1",
            plan_id="trial",
            status="trialing",
            trial_started_at=NOW - timedelta(days=15),
            trial_ends_at=NOW - timedelta(days=1),
        )
    )

    result = repo.consume_usage(
        "org-1",
        "analyst_questions",
        now=NOW,
    )
    assert result.allowed is False
    assert result.remaining == 0
    assert repo.get_usage("org-1", now=NOW).counts == {}


def test_usage_release_restores_reserved_capacity() -> None:
    repo = CommercialRepository(MemoryStore())

    reserved = repo.consume_usage(
        "org-1",
        "analyst_questions",
        now=NOW,
    )
    assert reserved.allowed is True
    assert reserved.usage.used("analyst_questions") == 1

    released = repo.release_usage(
        "org-1",
        "analyst_questions",
        now=NOW,
    )
    assert released.used("analyst_questions") == 0
