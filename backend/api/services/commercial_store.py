from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from ..config import settings
from ..persistence import LocalJsonDocumentStore, PostgresJsonDocumentStore
from .. import runtime_persistence
from .commercial import (
    EntitlementSnapshot,
    SubscriptionSnapshot,
    UsageSnapshot,
    build_entitlements,
    get_plan,
)


class CommercialDocumentStore(Protocol):
    def read(self, key: str) -> Any | None: ...
    def write(self, key: str, value: Any) -> None: ...


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class CommercialRepository:
    """Persistent organization-level commercial state.

    Payment processing is deliberately outside this repository. The repository
    owns the product's internal subscription snapshot and can later be driven by
    a verified payment-provider webhook adapter.
    """

    def __init__(self, store: CommercialDocumentStore) -> None:
        self.store = store

    def get_subscription(self, organization_id: str, *, now: datetime) -> SubscriptionSnapshot:
        key = f"subscription:{organization_id}"
        raw = self.store.read(key)
        if raw is None:
            subscription = SubscriptionSnapshot(
                organization_id=organization_id,
                plan_id="trial",
                status="trialing",
                trial_started_at=now,
                trial_ends_at=now + timedelta(days=get_plan("trial").trial_days),
            )
            self.store.write(key, {
                "organization_id": subscription.organization_id,
                "plan_id": subscription.plan_id,
                "status": subscription.status,
                "trial_started_at": _iso(subscription.trial_started_at),
                "trial_ends_at": _iso(subscription.trial_ends_at),
                "current_period_start": None,
                "current_period_end": None,
            })
            return subscription

        return SubscriptionSnapshot(
            organization_id=str(raw["organization_id"]),
            plan_id=str(raw["plan_id"]),
            status=str(raw["status"]),
            trial_started_at=_parse(raw.get("trial_started_at")),
            trial_ends_at=_parse(raw.get("trial_ends_at")),
            current_period_start=_parse(raw.get("current_period_start")),
            current_period_end=_parse(raw.get("current_period_end")),
        )

    def save_subscription(self, subscription: SubscriptionSnapshot) -> None:
        self.store.write(
            f"subscription:{subscription.organization_id}",
            {
                "organization_id": subscription.organization_id,
                "plan_id": subscription.plan_id,
                "status": subscription.status,
                "trial_started_at": _iso(subscription.trial_started_at) if subscription.trial_started_at else None,
                "trial_ends_at": _iso(subscription.trial_ends_at) if subscription.trial_ends_at else None,
                "current_period_start": _iso(subscription.current_period_start) if subscription.current_period_start else None,
                "current_period_end": _iso(subscription.current_period_end) if subscription.current_period_end else None,
            },
        )

    def get_usage(self, organization_id: str) -> UsageSnapshot:
        raw = self.store.read(f"usage:{organization_id}")
        if not raw:
            return UsageSnapshot(counts={})
        return UsageSnapshot(
            counts={
                metric: max(0, int(value))
                for metric, value in raw.get("counts", {}).items()
            }
        )

    def get_entitlements(self, organization_id: str, *, now: datetime) -> EntitlementSnapshot:
        subscription = self.get_subscription(organization_id, now=now)
        usage = self.get_usage(organization_id)
        return build_entitlements(subscription, usage, now=now)


def runtime_commercial_repository() -> CommercialRepository:
    """Create the repository against the configured runtime persistence backend."""
    if settings.persistence_mode == "external":
        if runtime_persistence._provider is None:
            raise RuntimeError("External runtime persistence was accessed before lifecycle startup.")
        # The shared V4 JSON document table is namespaced, so commercial state
        # remains isolated from datasets/sessions/monitoring documents.
        store = PostgresJsonDocumentStore(
            settings.database_url,
            "commercial",
            provider=runtime_persistence._provider,
        )
        return CommercialRepository(store)

    # Local development uses the same JSON document semantics with a dedicated
    # commercial root, keeping billing state out of analytical artifacts.
    runtime_persistence.get_runtime_persistence()
    store = LocalJsonDocumentStore(settings.runtime_root / "runtime_commercial")
    return CommercialRepository(store)
