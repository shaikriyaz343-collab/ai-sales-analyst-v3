from datetime import datetime, timezone

from backend.api.services.commercial_store import CommercialRepository
from backend.api.services.payment_provider import WebhookEvent


NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


class MemoryStore:
    def __init__(self) -> None:
        self.items = {}

    def read(self, key):
        return self.items.get(key)

    def write(self, key, value):
        self.items[key] = value


def event(event_id: str, occurred_at: str, price_id: str = "pri_starter") -> WebhookEvent:
    return WebhookEvent(
        provider="paddle",
        event_id=event_id,
        event_type="subscription.updated",
        received_at=NOW,
        payload={
            "event_id": event_id,
            "event_type": "subscription.updated",
            "occurred_at": occurred_at,
            "data": {
                "id": "sub_123",
                "status": "active",
                "customer_id": "ctm_123",
                "custom_data": {"organization_id": "org-1"},
                "items": [{"price": {"id": price_id}}],
                "current_billing_period": {
                    "starts_at": "2026-09-18T12:00:00Z",
                    "ends_at": "2026-10-18T12:00:00Z",
                },
            },
        },
    )


def price_to_plan(price_id: str) -> str | None:
    return {"pri_starter": "starter", "pri_growth": "growth"}.get(price_id)


def test_provider_event_updates_subscription_and_is_idempotent() -> None:
    store = MemoryStore()
    repo = CommercialRepository(store)

    assert repo.apply_webhook_event(event("evt_1", "2026-09-18T12:00:00Z"), plan_for_price=price_to_plan) is True
    assert repo.apply_webhook_event(event("evt_1", "2026-09-18T12:00:00Z"), plan_for_price=price_to_plan) is False

    subscription = repo.find_subscription("org-1")
    assert subscription is not None
    assert subscription.plan_id == "starter"
    assert subscription.provider_subscription_id == "sub_123"
    assert subscription.provider_customer_id == "ctm_123"
    assert subscription.provider_price_id == "pri_starter"
    assert subscription.provider_updated_at == NOW


def test_older_provider_event_cannot_roll_back_newer_state() -> None:
    store = MemoryStore()
    repo = CommercialRepository(store)

    assert repo.apply_webhook_event(event("evt_new", "2026-09-18T12:10:00Z", price_id="pri_growth"), plan_for_price=price_to_plan)
    assert repo.apply_webhook_event(event("evt_old", "2026-09-18T12:05:00Z", price_id="pri_starter"), plan_for_price=price_to_plan) is False

    subscription = repo.find_subscription("org-1")
    assert subscription is not None
    assert subscription.plan_id == "growth"
    assert subscription.provider_price_id == "pri_growth"


def test_reconcile_subscription_applies_provider_state() -> None:
    store = MemoryStore()
    repo = CommercialRepository(store)

    changed = repo.reconcile_subscription(
        {
            "id": "sub_123",
            "status": "active",
            "customer_id": "ctm_123",
            "custom_data": {"organization_id": "org-1", "plan_id": "starter"},
            "items": [{"price": {"id": "pri_starter"}}],
            "current_billing_period": {
                "starts_at": "2026-09-18T12:00:00Z",
                "ends_at": "2026-10-18T12:00:00Z",
            },
            "updated_at": "2026-09-18T12:05:00Z",
        },
        plan_for_price=price_to_plan,
    )

    assert changed is True
    subscription = repo.find_subscription("org-1")
    assert subscription is not None
    assert subscription.status == "active"
    assert subscription.provider_subscription_id == "sub_123"
