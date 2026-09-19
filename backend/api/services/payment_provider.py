from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import time
from typing import Any, Protocol

import httpx


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
    """Provider-neutral contract for checkout and verified webhooks."""

    name: str

    def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSession: ...

    def verify_webhook(self, payload: bytes, signature: str) -> WebhookEvent: ...

    def get_customer_portal_url(self, provider_customer_id: str, return_url: str) -> str: ...


class PaddleProvider:
    """Paddle Billing adapter using the server-side API and signed webhooks."""

    name = "paddle"

    def __init__(
        self,
        *,
        api_key: str,
        webhook_secret: str,
        environment: str,
        starter_price_id: str,
        growth_price_id: str,
    ) -> None:
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.environment = environment
        self.price_ids = {
            "starter": starter_price_id,
            "growth": growth_price_id,
        }
        self.base_url = (
            "https://sandbox-api.paddle.com"
            if environment == "sandbox"
            else "https://api.paddle.com"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Paddle-Version": "1",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                timeout=10.0,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise PaymentProviderError("Paddle request could not be completed.") from exc
        if response.status_code >= 400:
            raise PaymentProviderError("Paddle rejected the billing request.")
        try:
            return response.json()
        except ValueError as exc:
            raise PaymentProviderError("Paddle returned an invalid response.") from exc

    def price_for_plan(self, plan_id: str) -> str:
        try:
            return self.price_ids[plan_id]
        except KeyError as exc:
            raise PaymentProviderError(f"Unsupported paid plan: {plan_id}") from exc

    def plan_for_price(self, price_id: str) -> str | None:
        for plan_id, configured_price_id in self.price_ids.items():
            if configured_price_id == price_id:
                return plan_id
        return None

    def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSession:
        price_id = self.price_for_plan(request.plan_id)
        result = self._request(
            "POST",
            "/transactions",
            json={
                "items": [{"price_id": price_id, "quantity": 1}],
                "collection_mode": "automatic",
                "custom_data": {
                    "organization_id": request.organization_id,
                    "plan_id": request.plan_id,
                },
            },
        )
        data = result.get("data") or {}
        transaction_id = data.get("id")
        checkout_url = (data.get("checkout") or {}).get("url")
        if not transaction_id or not checkout_url:
            raise PaymentProviderError("Paddle did not return a checkout link.")
        return CheckoutSession(
            provider=self.name,
            provider_session_id=str(transaction_id),
            checkout_url=str(checkout_url),
        )

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        if not subscription_id.startswith("sub_"):
            raise PaymentProviderError("Invalid Paddle subscription identifier.")
        result = self._request("GET", f"/subscriptions/{subscription_id}")
        data = result.get("data")
        if not isinstance(data, dict) or not data.get("id"):
            raise PaymentProviderError("Paddle did not return the subscription.")
        return data

    def verify_webhook(self, payload: bytes, signature: str) -> WebhookEvent:
        if not signature:
            raise PaymentProviderError("Missing Paddle webhook signature.")

        parts: dict[str, list[str]] = {}
        for item in signature.split(";"):
            key, sep, value = item.partition("=")
            if sep and key:
                parts.setdefault(key, []).append(value)

        timestamps = parts.get("ts", [])
        signatures = parts.get("h1", [])
        if not timestamps or not signatures:
            raise PaymentProviderError("Invalid Paddle webhook signature.")

        try:
            timestamp = int(timestamps[0])
        except ValueError as exc:
            raise PaymentProviderError("Invalid Paddle webhook timestamp.") from exc

        if abs(int(time.time()) - timestamp) > 5:
            raise PaymentProviderError("Expired Paddle webhook event.")

        signed_payload = f"{timestamp}:".encode("utf-8") + payload
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
            raise PaymentProviderError("Invalid Paddle webhook signature.")

        try:
            data = __import__("json").loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise PaymentProviderError("Invalid Paddle webhook payload.") from exc

        event_id = data.get("event_id")
        event_type = data.get("event_type")
        if not event_id or not event_type:
            raise PaymentProviderError("Paddle webhook payload is incomplete.")

        return WebhookEvent(
            provider=self.name,
            event_id=str(event_id),
            event_type=str(event_type),
            received_at=datetime.now(timezone.utc),
            payload=data,
        )

    def get_customer_portal_url(self, provider_customer_id: str, return_url: str) -> str:
        result = self._request(
            "POST",
            f"/customers/{provider_customer_id}/portal-sessions",
            json={},
        )
        overview = ((result.get("data") or {}).get("urls") or {}).get("general", {}).get("overview")
        if not overview:
            raise PaymentProviderError("Paddle did not return a customer portal URL.")
        return str(overview)
