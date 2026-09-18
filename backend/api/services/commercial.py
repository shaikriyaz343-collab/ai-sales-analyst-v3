from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final, Literal


SubscriptionStatus = Literal[
    "trialing",
    "active",
    "past_due",
    "canceled",
    "expired",
]

UsageMetric = Literal[
    "dataset_uploads",
    "analyst_questions",
    "reports",
    "monitoring_rules",
    "saved_intelligence",
]


@dataclass(frozen=True)
class Plan:
    plan_id: str
    name: str
    price_usd_monthly: int
    trial_days: int
    max_seats: int
    max_workspaces: int
    monthly_limits: dict[UsageMetric, int | None]
    features: frozenset[str]

    def limit_for(self, metric: UsageMetric) -> int | None:
        return self.monthly_limits.get(metric)


@dataclass(frozen=True)
class SubscriptionSnapshot:
    organization_id: str
    plan_id: str
    status: SubscriptionStatus
    trial_started_at: datetime | None = None
    trial_ends_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


@dataclass(frozen=True)
class UsageSnapshot:
    counts: dict[UsageMetric, int]

    def used(self, metric: UsageMetric) -> int:
        return max(0, int(self.counts.get(metric, 0)))


@dataclass(frozen=True)
class EntitlementSnapshot:
    organization_id: str
    plan_id: str | None
    plan_name: str | None
    access_active: bool
    access_reason: str
    max_seats: int
    max_workspaces: int
    features: frozenset[str]
    usage: UsageSnapshot
    remaining: dict[UsageMetric, int | None]

    def allows_feature(self, feature: str) -> bool:
        return self.access_active and feature in self.features

    def allows_usage(self, metric: UsageMetric, additional: int = 1) -> bool:
        if not self.access_active or additional < 0:
            return False
        limit = self.remaining.get(metric)
        return limit is None or limit >= additional


PLAN_CATALOG: Final[dict[str, Plan]] = {
    "trial": Plan(
        plan_id="trial",
        name="14-day Trial",
        price_usd_monthly=0,
        trial_days=14,
        max_seats=2,
        max_workspaces=1,
        monthly_limits={
            "dataset_uploads": 3,
            "analyst_questions": 50,
            "reports": 5,
            "monitoring_rules": 3,
            "saved_intelligence": 10,
        },
        features=frozenset({
            "overview",
            "decisions",
            "explore",
            "forecast",
            "ask",
            "reports",
            "monitoring",
            "saved_intelligence",
            "actions",
        }),
    ),
    "starter": Plan(
        plan_id="starter",
        name="Starter",
        price_usd_monthly=49,
        trial_days=0,
        max_seats=5,
        max_workspaces=3,
        monthly_limits={
            "dataset_uploads": 25,
            "analyst_questions": 500,
            "reports": 50,
            "monitoring_rules": 10,
            "saved_intelligence": 100,
        },
        features=frozenset({
            "overview",
            "decisions",
            "explore",
            "forecast",
            "ask",
            "reports",
            "monitoring",
            "saved_intelligence",
            "actions",
        }),
    ),
    "growth": Plan(
        plan_id="growth",
        name="Growth",
        price_usd_monthly=149,
        trial_days=0,
        max_seats=15,
        max_workspaces=10,
        monthly_limits={
            "dataset_uploads": 200,
            "analyst_questions": 2500,
            "reports": 250,
            "monitoring_rules": 50,
            "saved_intelligence": 500,
        },
        features=frozenset({
            "overview",
            "decisions",
            "explore",
            "forecast",
            "ask",
            "reports",
            "monitoring",
            "saved_intelligence",
            "actions",
        }),
    ),
}


def get_plan(plan_id: str) -> Plan:
    try:
        return PLAN_CATALOG[plan_id]
    except KeyError as exc:
        raise ValueError(f"Unknown commercial plan: {plan_id}") from exc


def _trial_active(subscription: SubscriptionSnapshot, now: datetime) -> bool:
    if subscription.status != "trialing":
        return False
    if subscription.trial_ends_at is None:
        return False
    return now < subscription.trial_ends_at


def _access_state(subscription: SubscriptionSnapshot, now: datetime) -> tuple[bool, str]:
    if subscription.status == "trialing":
        if _trial_active(subscription, now):
            return True, "trial_active"
        return False, "trial_expired"
    if subscription.status == "active":
        if subscription.current_period_end is not None and now >= subscription.current_period_end:
            return False, "billing_period_expired"
        return True, "active"
    if subscription.status == "past_due":
        return False, "past_due"
    if subscription.status == "canceled":
        if subscription.current_period_end is not None and now < subscription.current_period_end:
            return True, "canceled_end_of_period"
        return False, "canceled"
    if subscription.status == "expired":
        return False, "expired"
    raise ValueError(f"Unsupported subscription status: {subscription.status}")


def build_entitlements(
    subscription: SubscriptionSnapshot,
    usage: UsageSnapshot,
    *,
    now: datetime,
) -> EntitlementSnapshot:
    access_active, access_reason = _access_state(subscription, now)

    if not access_active:
        return EntitlementSnapshot(
            organization_id=subscription.organization_id,
            plan_id=None,
            plan_name=None,
            access_active=False,
            access_reason=access_reason,
            max_seats=0,
            max_workspaces=0,
            features=frozenset(),
            usage=usage,
            remaining={metric: 0 for metric in usage.counts},
        )

    plan = get_plan(subscription.plan_id)
    remaining: dict[UsageMetric, int | None] = {}
    for metric, limit in plan.monthly_limits.items():
        if limit is None:
            remaining[metric] = None
        else:
            remaining[metric] = max(0, limit - usage.used(metric))

    return EntitlementSnapshot(
        organization_id=subscription.organization_id,
        plan_id=plan.plan_id,
        plan_name=plan.name,
        access_active=True,
        access_reason=access_reason,
        max_seats=plan.max_seats,
        max_workspaces=plan.max_workspaces,
        features=plan.features,
        usage=usage,
        remaining=remaining,
    )


def plan_catalog() -> tuple[Plan, ...]:
    return tuple(PLAN_CATALOG.values())
