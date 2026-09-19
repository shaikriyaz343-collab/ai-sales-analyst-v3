from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Protocol

from .. import runtime_persistence
from ..config import settings
from ..persistence import LocalJsonDocumentStore, PostgresJsonDocumentStore
from .payment_provider import WebhookEvent

from .commercial import (
    EntitlementSnapshot,
    SubscriptionSnapshot,
    UsageConsumption,
    UsageMetric,
    UsageSnapshot,
    build_entitlements,
    get_plan,
    usage_period_start,
    validate_usage_metric,
)


class CommercialDocumentStore(Protocol):
    def read(self, key: str) -> Any | None: ...
    def write(self, key: str, value: Any) -> None: ...
    def list_prefix(self, prefix: str) -> list[tuple[str, Any]]: ...


class UsageMeter(Protocol):
    def get_counts(self, organization_id: str, period_start: datetime) -> dict[UsageMetric, int]: ...
    def increment(
        self,
        organization_id: str,
        period_start: datetime,
        metric: UsageMetric,
        amount: int,
    ) -> int: ...
    def consume(
        self,
        organization_id: str,
        period_start: datetime,
        metric: UsageMetric,
        amount: int,
        limit: int | None,
    ) -> tuple[bool, int]: ...
    def release(
        self,
        organization_id: str,
        period_start: datetime,
        metric: UsageMetric,
        amount: int,
    ) -> int: ...


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _trial_snapshot(organization_id: str, now: datetime) -> SubscriptionSnapshot:
    return SubscriptionSnapshot(
        organization_id=organization_id,
        plan_id="trial",
        status="trialing",
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=get_plan("trial").trial_days),
    )


class DocumentUsageMeter:
    """Development/test usage meter with thread-safe read-modify-write semantics."""

    _lock = RLock()

    def __init__(self, store: CommercialDocumentStore) -> None:
        self.store = store

    @staticmethod
    def _key(organization_id: str, period_start: datetime) -> str:
        return f"usage:{organization_id}:{period_start.astimezone(timezone.utc).isoformat()}"

    def get_counts(self, organization_id: str, period_start: datetime) -> dict[UsageMetric, int]:
        with self._lock:
            raw = self.store.read(self._key(organization_id, period_start)) or {}
            return {
                validate_usage_metric(metric): max(0, int(value))
                for metric, value in raw.get("counts", {}).items()
            }

    def _write_counts(self, organization_id: str, period_start: datetime, counts: dict[UsageMetric, int]) -> None:
        self.store.write(
            self._key(organization_id, period_start),
            {"period_start": _iso(period_start), "counts": counts},
        )

    def increment(
        self,
        organization_id: str,
        period_start: datetime,
        metric: UsageMetric,
        amount: int,
    ) -> int:
        if amount <= 0:
            raise ValueError("Usage increment must be greater than zero.")
        with self._lock:
            counts = self.get_counts(organization_id, period_start)
            counts[metric] = counts.get(metric, 0) + amount
            self._write_counts(organization_id, period_start, counts)
            return counts[metric]

    def consume(
        self,
        organization_id: str,
        period_start: datetime,
        metric: UsageMetric,
        amount: int,
        limit: int | None,
    ) -> tuple[bool, int]:
        if amount <= 0:
            raise ValueError("Usage increment must be greater than zero.")
        with self._lock:
            counts = self.get_counts(organization_id, period_start)
            current = counts.get(metric, 0)
            if limit is not None and current + amount > limit:
                return False, current
            counts[metric] = current + amount
            self._write_counts(organization_id, period_start, counts)
            return True, counts[metric]

    def release(
        self,
        organization_id: str,
        period_start: datetime,
        metric: UsageMetric,
        amount: int,
    ) -> int:
        if amount <= 0:
            raise ValueError("Usage release must be greater than zero.")
        with self._lock:
            counts = self.get_counts(organization_id, period_start)
            current = counts.get(metric, 0)
            new_count = max(0, current - amount)
            if new_count == 0:
                counts.pop(metric, None)
            else:
                counts[metric] = new_count
            self._write_counts(organization_id, period_start, counts)
            return new_count


class PostgresUsageMeter:
    """Production usage meter using atomic PostgreSQL transactions."""

    TABLE = "v4_commercial_usage"

    def __init__(self, provider: Any) -> None:
        self.provider = provider
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.provider.connection() as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    organization_id TEXT NOT NULL,
                    period_start TIMESTAMPTZ NOT NULL,
                    metric TEXT NOT NULL,
                    usage_count BIGINT NOT NULL CHECK (usage_count >= 0),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (organization_id, period_start, metric)
                )
                """
            )
            conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_v4_commercial_usage_org_period
                ON {self.TABLE}(organization_id, period_start)
                """
            )
            conn.commit()

    def get_counts(self, organization_id: str, period_start: datetime) -> dict[UsageMetric, int]:
        with self.provider.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT metric, usage_count
                FROM {self.TABLE}
                WHERE organization_id = %s AND period_start = %s
                ORDER BY metric
                """,
                (organization_id, period_start),
            ).fetchall()
        return {
            validate_usage_metric(str(metric)): max(0, int(count))
            for metric, count in rows
        }

    def increment(
        self,
        organization_id: str,
        period_start: datetime,
        metric: UsageMetric,
        amount: int,
    ) -> int:
        if amount <= 0:
            raise ValueError("Usage increment must be greater than zero.")
        with self.provider.connection() as conn:
            row = conn.execute(
                f"""
                INSERT INTO {self.TABLE}(organization_id, period_start, metric, usage_count, updated_at)
                VALUES(%s, %s, %s, %s, NOW())
                ON CONFLICT(organization_id, period_start, metric)
                DO UPDATE SET
                    usage_count = {self.TABLE}.usage_count + EXCLUDED.usage_count,
                    updated_at = NOW()
                RETURNING usage_count
                """,
                (organization_id, period_start, metric, amount),
            ).fetchone()
            conn.commit()
        return int(row[0])

    def consume(
        self,
        organization_id: str,
        period_start: datetime,
        metric: UsageMetric,
        amount: int,
        limit: int | None,
    ) -> tuple[bool, int]:
        if amount <= 0:
            raise ValueError("Usage increment must be greater than zero.")
        if limit is None:
            return True, self.increment(organization_id, period_start, metric, amount)

        with self.provider.connection() as conn:
            row = conn.execute(
                f"""
                SELECT usage_count
                FROM {self.TABLE}
                WHERE organization_id = %s AND period_start = %s AND metric = %s
                FOR UPDATE
                """,
                (organization_id, period_start, metric),
            ).fetchone()

            current = int(row[0]) if row else 0
            if current + amount > limit:
                conn.rollback()
                return False, current

            if row:
                new_count = conn.execute(
                    f"""
                    UPDATE {self.TABLE}
                    SET usage_count = usage_count + %s, updated_at = NOW()
                    WHERE organization_id = %s AND period_start = %s AND metric = %s
                    RETURNING usage_count
                    """,
                    (amount, organization_id, period_start, metric),
                ).fetchone()[0]
            else:
                new_count = conn.execute(
                    f"""
                    INSERT INTO {self.TABLE}(organization_id, period_start, metric, usage_count, updated_at)
                    VALUES(%s, %s, %s, %s, NOW())
                    RETURNING usage_count
                    """,
                    (organization_id, period_start, metric, amount),
                ).fetchone()[0]

            conn.commit()
            return True, int(new_count)

    def release(
        self,
        organization_id: str,
        period_start: datetime,
        metric: UsageMetric,
        amount: int,
    ) -> int:
        if amount <= 0:
            raise ValueError("Usage release must be greater than zero.")
        with self.provider.connection() as conn:
            row = conn.execute(
                f"""
                UPDATE {self.TABLE}
                SET usage_count = GREATEST(0, usage_count - %s),
                    updated_at = NOW()
                WHERE organization_id = %s AND period_start = %s AND metric = %s
                RETURNING usage_count
                """,
                (amount, organization_id, period_start, metric),
            ).fetchone()
            conn.commit()
        return int(row[0]) if row else 0


class CommercialRepository:
    """Persistent organization-level commercial state plus period-aware usage meters."""

    def __init__(
        self,
        store: CommercialDocumentStore,
        usage_meter: UsageMeter | None = None,
    ) -> None:
        self.store = store
        self.usage_meter = usage_meter or DocumentUsageMeter(store)

    def find_subscription(self, organization_id: str) -> SubscriptionSnapshot | None:
        raw = self.store.read(f"subscription:{organization_id}")
        if raw is None:
            return None
        return SubscriptionSnapshot(
            organization_id=str(raw["organization_id"]),
            plan_id=str(raw["plan_id"]),
            status=str(raw["status"]),
            trial_started_at=_parse(raw.get("trial_started_at")),
            trial_ends_at=_parse(raw.get("trial_ends_at")),
            current_period_start=_parse(raw.get("current_period_start")),
            current_period_end=_parse(raw.get("current_period_end")),
            provider=str(raw["provider"]) if raw.get("provider") else None,
            provider_customer_id=str(raw["provider_customer_id"]) if raw.get("provider_customer_id") else None,
            provider_subscription_id=str(raw["provider_subscription_id"]) if raw.get("provider_subscription_id") else None,
            provider_price_id=str(raw["provider_price_id"]) if raw.get("provider_price_id") else None,
            provider_updated_at=_parse(raw.get("provider_updated_at")),
        )

    def get_subscription(self, organization_id: str, *, now: datetime) -> SubscriptionSnapshot:
        existing = self.find_subscription(organization_id)
        if existing is not None:
            return existing

        subscription = _trial_snapshot(organization_id, now)
        self.save_subscription(subscription)
        return subscription

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
                "provider": subscription.provider,
                "provider_customer_id": subscription.provider_customer_id,
                "provider_subscription_id": subscription.provider_subscription_id,
                "provider_price_id": subscription.provider_price_id,
                "provider_updated_at": _iso(subscription.provider_updated_at) if subscription.provider_updated_at else None,
            },
        )

    def apply_webhook_event(self, event: Any, *, plan_for_price) -> bool:
        """Apply a verified provider subscription event idempotently."""
        event_key = f"webhook:{event.provider}:{event.event_id}"
        if self.store.read(event_key) is not None:
            return False

        supported = {
            "subscription.created",
            "subscription.updated",
            "subscription.reconciled",
            "subscription.activated",
            "subscription.trialing",
            "subscription.past_due",
            "subscription.paused",
            "subscription.resumed",
            "subscription.canceled",
        }
        if event.event_type not in supported:
            self.store.write(event_key, {"processed_at": _iso(event.received_at), "ignored": True})
            return False

        payload = event.payload
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("Provider webhook data is missing.")

        custom_data = data.get("custom_data")
        custom_data = custom_data if isinstance(custom_data, dict) else {}
        organization_id = custom_data.get("organization_id")
        if not organization_id:
            raise ValueError("Provider webhook is missing organization identity.")

        status = str(data.get("status") or "")
        if status == "paused":
            normalized_status = "paused"
        elif status in {"trialing", "active", "past_due", "canceled"}:
            normalized_status = status
        else:
            raise ValueError("Provider webhook has an unsupported subscription status.")

        items = data.get("items")
        price_id = None
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                price = item.get("price")
                if isinstance(price, dict) and price.get("id"):
                    price_id = str(price["id"])
                    break

        configured_plan = custom_data.get("plan_id")
        plan_id = str(configured_plan) if configured_plan in {"starter", "growth"} else None
        if price_id:
            resolved_plan = plan_for_price(price_id)
            if resolved_plan:
                plan_id = resolved_plan
        if plan_id is None:
            raise ValueError("Provider webhook could not be mapped to a paid plan.")

        occurred_at = _parse(payload.get("occurred_at")) or event.received_at
        existing = self.find_subscription(str(organization_id))
        if existing and existing.provider_updated_at and occurred_at < existing.provider_updated_at:
            self.store.write(
                event_key,
                {"processed_at": _iso(event.received_at), "ignored": "out_of_order"},
            )
            return False

        billing_period = data.get("current_billing_period")
        billing_period = billing_period if isinstance(billing_period, dict) else {}
        trial_started_at = None
        trial_ends_at = None
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                trial = item.get("trial_dates")
                if isinstance(trial, dict):
                    trial_started_at = _parse(trial.get("starts_at"))
                    trial_ends_at = _parse(trial.get("ends_at"))
                    if trial_started_at or trial_ends_at:
                        break

        subscription = SubscriptionSnapshot(
            organization_id=str(organization_id),
            plan_id=plan_id,
            status=normalized_status,
            trial_started_at=trial_started_at,
            trial_ends_at=trial_ends_at,
            current_period_start=_parse(billing_period.get("starts_at")),
            current_period_end=_parse(billing_period.get("ends_at")),
            provider=event.provider,
            provider_customer_id=str(data["customer_id"]) if data.get("customer_id") else None,
            provider_subscription_id=str(data["id"]) if data.get("id") else None,
            provider_price_id=price_id,
            provider_updated_at=occurred_at,
        )
        self.save_subscription(subscription)
        self.store.write(
            event_key,
            {
                "processed_at": _iso(event.received_at),
                "event_type": event.event_type,
                "occurred_at": _iso(occurred_at),
                "organization_id": str(organization_id),
            },
        )
        return True

    def list_subscriptions(self) -> list[SubscriptionSnapshot]:
        store_list = getattr(self.store, "list_prefix", None)
        if not callable(store_list):
            return []
        snapshots: list[SubscriptionSnapshot] = []
        for key, raw in store_list("subscription:"):
            if not isinstance(raw, dict) or not key.startswith("subscription:"):
                continue
            organization_id = key[len("subscription:"):]
            if not organization_id:
                continue
            snapshot = self.find_subscription(organization_id)
            if snapshot is not None:
                snapshots.append(snapshot)
        return [snapshot for snapshot in snapshots if snapshot is not None]

    def reconcile_subscription(
        self,
        subscription_payload: dict[str, Any],
        *,
        plan_for_price,
    ) -> bool:
        occurred_at = subscription_payload.get("updated_at") or datetime.now(timezone.utc).isoformat()
        subscription_id = str(subscription_payload.get("id") or "")
        if not subscription_id:
            raise ValueError("Provider reconciliation payload has no subscription ID.")

        event = WebhookEvent(
            provider="paddle",
            event_id=f"reconcile:{subscription_id}:{occurred_at}",
            event_type="subscription.reconciled",
            received_at=datetime.now(timezone.utc),
            payload={
                "event_id": f"reconcile:{subscription_id}:{occurred_at}",
                "event_type": "subscription.reconciled",
                "occurred_at": occurred_at,
                "data": subscription_payload,
            },
        )
        return self.apply_webhook_event(event, plan_for_price=plan_for_price)

    def get_usage(self, organization_id: str, *, now: datetime) -> UsageSnapshot:
        subscription = self.find_subscription(organization_id) or _trial_snapshot(organization_id, now)
        period_start = usage_period_start(subscription, now)
        return UsageSnapshot(
            counts=self.usage_meter.get_counts(organization_id, period_start),
            period_start=period_start,
        )

    def record_usage(
        self,
        organization_id: str,
        metric: UsageMetric,
        *,
        amount: int = 1,
        now: datetime,
    ) -> UsageSnapshot:
        validate_usage_metric(metric)
        subscription = self.get_subscription(organization_id, now=now)
        period_start = usage_period_start(subscription, now)
        self.usage_meter.increment(organization_id, period_start, metric, amount)
        return UsageSnapshot(
            counts=self.usage_meter.get_counts(organization_id, period_start),
            period_start=period_start,
        )

    def consume_usage(
        self,
        organization_id: str,
        metric: UsageMetric,
        *,
        amount: int = 1,
        now: datetime,
    ) -> UsageConsumption:
        validate_usage_metric(metric)
        if amount <= 0:
            raise ValueError("Usage increment must be greater than zero.")

        subscription = self.get_subscription(organization_id, now=now)
        usage = UsageSnapshot(
            counts=self.usage_meter.get_counts(
                organization_id,
                usage_period_start(subscription, now),
            ),
            period_start=usage_period_start(subscription, now),
        )
        entitlements = build_entitlements(subscription, usage, now=now)
        if not entitlements.access_active:
            return UsageConsumption(
                allowed=False,
                usage=usage,
                remaining=0,
            )

        limit = get_plan(subscription.plan_id).limit_for(metric)
        allowed, new_count = self.usage_meter.consume(
            organization_id,
            usage.period_start or usage_period_start(subscription, now),
            metric,
            amount,
            limit,
        )
        remaining = None if limit is None else max(0, limit - new_count)
        new_usage = UsageSnapshot(
            counts={
                **usage.counts,
                metric: new_count,
            },
            period_start=usage.period_start,
        )
        return UsageConsumption(allowed=allowed, usage=new_usage, remaining=remaining)

    def release_usage(
        self,
        organization_id: str,
        metric: UsageMetric,
        *,
        amount: int = 1,
        now: datetime,
    ) -> UsageSnapshot:
        validate_usage_metric(metric)
        if amount <= 0:
            raise ValueError("Usage release must be greater than zero.")

        subscription = self.get_subscription(organization_id, now=now)
        period_start = usage_period_start(subscription, now)
        self.usage_meter.release(
            organization_id,
            period_start,
            metric,
            amount,
        )
        return UsageSnapshot(
            counts=self.usage_meter.get_counts(organization_id, period_start),
            period_start=period_start,
        )

    def get_entitlements(self, organization_id: str, *, now: datetime) -> EntitlementSnapshot:
        # A GET entitlement lookup is intentionally read-only.
        subscription = self.find_subscription(organization_id) or _trial_snapshot(organization_id, now)
        usage = self.get_usage(organization_id, now=now)
        return build_entitlements(subscription, usage, now=now)


_runtime_repository: CommercialRepository | None = None


def runtime_commercial_repository() -> CommercialRepository:
    """Return one process-local commercial repository for the active runtime."""
    global _runtime_repository
    if _runtime_repository is not None:
        return _runtime_repository
    if settings.persistence_mode == "external":
        if runtime_persistence._provider is None:
            raise RuntimeError("External runtime persistence was accessed before lifecycle startup.")
        document_store = PostgresJsonDocumentStore(
            settings.database_url,
            "commercial",
            provider=runtime_persistence._provider,
        )
        usage_meter = PostgresUsageMeter(runtime_persistence._provider)
        _runtime_repository = CommercialRepository(document_store, usage_meter=usage_meter)
        return _runtime_repository

    runtime_persistence.get_runtime_persistence()
    store = LocalJsonDocumentStore(settings.runtime_root / "runtime_commercial")
    _runtime_repository = CommercialRepository(store)
    return _runtime_repository


def reset_runtime_commercial_repository() -> None:
    global _runtime_repository
    _runtime_repository = None