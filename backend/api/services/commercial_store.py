from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Protocol

from .. import runtime_persistence
from ..config import settings
from ..persistence import LocalJsonDocumentStore, PostgresJsonDocumentStore
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
            },
        )

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

    def get_entitlements(self, organization_id: str, *, now: datetime) -> EntitlementSnapshot:
        # A GET entitlement lookup is intentionally read-only.
        subscription = self.find_subscription(organization_id) or _trial_snapshot(organization_id, now)
        usage = self.get_usage(organization_id, now=now)
        return build_entitlements(subscription, usage, now=now)


def runtime_commercial_repository() -> CommercialRepository:
    """Create the repository against the configured runtime persistence backend."""
    if settings.persistence_mode == "external":
        if runtime_persistence._provider is None:
            raise RuntimeError("External runtime persistence was accessed before lifecycle startup.")
        document_store = PostgresJsonDocumentStore(
            settings.database_url,
            "commercial",
            provider=runtime_persistence._provider,
        )
        usage_meter = PostgresUsageMeter(runtime_persistence._provider)
        return CommercialRepository(document_store, usage_meter=usage_meter)

    runtime_persistence.get_runtime_persistence()
    store = LocalJsonDocumentStore(settings.runtime_root / "runtime_commercial")
    return CommercialRepository(store)
