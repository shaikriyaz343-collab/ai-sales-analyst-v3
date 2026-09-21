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
    customer_name: str


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
            code = None
            detail = None
            request_id = None
            try:
                body = response.json()
                errors = body.get("errors") if isinstance(body, dict) else None
                if isinstance(errors, list) and errors:
                    first = errors[0] if isinstance(errors[0], dict) else {}
                    code = first.get("code")
                    detail = first.get("detail") or first.get("message")
                error = body.get("error") if isinstance(body, dict) else None
                if isinstance(error, dict):
                    code = code or error.get("code")
                    detail = detail or error.get("detail") or error.get("message")
                meta = body.get("meta") if isinstance(body, dict) else None
                if isinstance(meta, dict):
                    request_id = meta.get("request_id")
            except ValueError:
                pass

            parts = [f"HTTP {response.status_code}"]
            if code:
                parts.append(f"code={code}")
            if request_id:
                parts.append(f"request_id={request_id}")
            if detail:
                parts.append(f"detail={' '.join(str(detail).split())[:300]}")
            raise PaymentProviderError("Paddle request rejected: " + ", ".join(parts))
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

    def get_or_create_customer(self, *, email: str, name: str, organization_id: str) -> str:
        listed = self._request(
            "GET",
            "/customers",
            params={"email": email, "per_page": 1},
        )
        data = listed.get("data") or []
        if data:
            customer = data[0] if isinstance(data[0], dict) else {}
            customer_id = customer.get("id")
            custom_data = customer.get("custom_data") or {}
            linked_org = custom_data.get("organization_id") if isinstance(custom_data, dict) else None
            if customer_id and linked_org == organization_id:
                return str(customer_id)
            if customer_id and linked_org:
                raise PaymentProviderError("Paddle customer is already linked to another organization.")
            raise PaymentProviderError("Existing Paddle customer is not linked to this organization.")

        result = self._request(
            "POST",
            "/customers",
            json={
                "email": email,
                "name": name or None,
                "custom_data": {"organization_id": organization_id},
            },
        )
        customer = result.get("data") or {}
        customer_id = customer.get("id")
        if not customer_id:
            raise PaymentProviderError("Paddle did not return a customer ID.")
        return str(customer_id)

    def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSession:
        price_id = self.price_for_plan(request.plan_id)
        customer_id = self.get_or_create_customer(
            email=request.customer_email,
            name=request.customer_name,
            organization_id=request.organization_id,
        )
        result = self._request(
            "POST",
            "/transactions",
            json={
                "customer_id": customer_id,
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

    def get_customer_portal_url(
        self,
        provider_customer_id: str,
        return_url: str,
        subscription_id: str | None = None,
    ) -> str:
        payload = {"subscription_ids": [subscription_id]} if subscription_id else {}
        result = self._request(
            "POST",
            f"/customers/{provider_customer_id}/portal-sessions",
            json=payload,
        )
        overview = ((result.get("data") or {}).get("urls") or {}).get("general", {}).get("overview")
        if not overview:
            raise PaymentProviderError("Paddle did not return a customer portal URL.")
        return str(overview)
