from datetime import datetime, timedelta, timezone

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
    assert set(store.items) == {"subscription:org-1"}


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


def test_repository_returns_commercial_entitlements() -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)

    entitlements = repository.get_entitlements("org-1", now=NOW)

    assert entitlements.access_active is True
    assert entitlements.plan_id == "trial"
    assert entitlements.plan_name == "14-day Trial"
    assert entitlements.remaining["analyst_questions"] == 50
