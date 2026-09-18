from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from backend.api.services.commercial import SubscriptionSnapshot, UsageSnapshot, usage_period_start
from backend.api.services.commercial_store import CommercialRepository


NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


class MemoryStore:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def read(self, key: str):
        return self.items.get(key)

    def write(self, key: str, value: dict) -> None:
        self.items[key] = value


def test_repository_initializes_trial_once() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)

    first = repository.get_subscription("org-1", now=NOW)
    second = repository.get_subscription("org-1", now=NOW + timedelta(days=1))

    assert first.plan_id == "trial"
    assert first.status == "trialing"
    assert first.trial_started_at == NOW
    assert first.trial_ends_at == NOW + timedelta(days=14)
    assert second == first


def test_repository_round_trips_paid_subscription() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)

    subscription = repository.get_subscription("org-1", now=NOW)
    updated = subscription.__class__(
        organization_id=subscription.organization_id,
        plan_id="starter",
        status="active",
        trial_started_at=subscription.trial_started_at,
        trial_ends_at=subscription.trial_ends_at,
        current_period_start=NOW,
        current_period_end=NOW + timedelta(days=30),
    )
    repository.save_subscription(updated)

    loaded = repository.get_subscription("org-1", now=NOW + timedelta(days=2))

    assert loaded.plan_id == "starter"
    assert loaded.status == "active"
    assert loaded.current_period_start == NOW
    assert loaded.current_period_end == NOW + timedelta(days=30)


def test_trial_usage_is_period_aware_and_persists() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)

    first = repository.record_usage("org-1", "analyst_questions", amount=3, now=NOW)
    second = repository.get_usage("org-1", now=NOW + timedelta(days=2))

    assert first.period_start == NOW
    assert second.period_start == NOW
    assert second.used("analyst_questions") == 3


def test_paid_usage_uses_billing_period_start() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)
    subscription = SubscriptionSnapshot(
        organization_id="org-1",
        plan_id="starter",
        status="active",
        current_period_start=NOW - timedelta(days=5),
        current_period_end=NOW + timedelta(days=25),
    )
    repository.save_subscription(subscription)

    first = repository.record_usage("org-1", "reports", now=NOW)
    later = repository.get_usage("org-1", now=NOW + timedelta(days=20))

    assert first.period_start == subscription.current_period_start
    assert later.period_start == subscription.current_period_start
    assert later.used("reports") == 1


def test_next_paid_period_does_not_reuse_previous_usage() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)
    current_period_start = NOW - timedelta(days=29)
    repository.save_subscription(
        SubscriptionSnapshot(
            organization_id="org-1",
            plan_id="starter",
            status="active",
            current_period_start=current_period_start,
            current_period_end=NOW + timedelta(days=1),
        )
    )
    repository.record_usage("org-1", "reports", amount=4, now=NOW)

    next_period_start = NOW + timedelta(days=2)
    repository.save_subscription(
        SubscriptionSnapshot(
            organization_id="org-1",
            plan_id="starter",
            status="active",
            current_period_start=next_period_start,
            current_period_end=next_period_start + timedelta(days=30),
        )
    )

    usage = repository.get_usage("org-1", now=next_period_start + timedelta(days=1))

    assert usage.period_start == next_period_start
    assert usage.used("reports") == 0


def test_concurrent_local_increments_do_not_lose_updates() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(
                repository.record_usage,
                "org-1",
                "analyst_questions",
                amount=1,
                now=NOW,
            )
            for _ in range(100)
        ]
        [future.result() for future in futures]

    usage = repository.get_usage("org-1", now=NOW)
    assert usage.used("analyst_questions") == 100


def test_consume_usage_is_limit_aware() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)

    first = [repository.consume_usage("org-1", "dataset_uploads", now=NOW) for _ in range(3)]
    fourth = repository.consume_usage("org-1", "dataset_uploads", now=NOW)

    assert all(item.allowed for item in first)
    assert fourth.allowed is False
    assert fourth.remaining == 0
    assert fourth.usage.used("dataset_uploads") == 3


def test_consume_usage_rejects_nonpositive_amount() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)

    with pytest.raises(ValueError, match="greater than zero"):
        repository.consume_usage("org-1", "reports", amount=0, now=NOW)


def test_repository_returns_commercial_entitlements_without_persisting_default_trial() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)

    entitlements = repository.get_entitlements("org-1", now=NOW)

    assert entitlements.access_active is True
    assert entitlements.plan_id == "trial"
    assert entitlements.plan_name == "14-day Trial"
    assert entitlements.usage.period_start == NOW
    assert entitlements.remaining["analyst_questions"] == 50
    assert store.items == {}


def test_usage_period_start_falls_back_to_utc_month_start() -> None:
    subscription = SubscriptionSnapshot(
        organization_id="org-1",
        plan_id="starter",
        status="expired",
    )

    assert usage_period_start(subscription, NOW) == datetime(2026, 9, 1, tzinfo=timezone.utc)
