from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class PaymentProviderError(RuntimeError):
    """Raised when a payment-provider operation cannot be completed."""


@dataclass(frozen=True)
class CheckoutRequest:
    organization_id: str
    plan_id: str
    customer_email: str
    success_url: str
    cancel_url: str


@dataclass(frozen=True)
class CheckoutSession:
    provider: str
    provider_session_id: str
    checkout_url: str
    expires_at: datetime | None = None


@dataclass(frozen=True)
class WebhookEvent:
    provider: str
    event_id: str
    event_type: str
    received_at: datetime
    payload: dict[str, Any]


class PaymentProvider(Protocol):
    """Provider-neutral contract for checkout and verified webhooks.

    Implementations must verify signatures before constructing WebhookEvent and
    must expose stable provider event IDs so the commercial repository can
    enforce idempotency.
    """

    name: str

    def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSession: ...

    def verify_webhook(self, payload: bytes, signature: str) -> WebhookEvent: ...

    def get_customer_portal_url(self, provider_customer_id: str, return_url: str) -> str: ...
