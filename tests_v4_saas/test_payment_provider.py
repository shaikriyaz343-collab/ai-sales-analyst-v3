from datetime import datetime, timezone
import hashlib
import hmac
import json
import time

import httpx
import pytest

from backend.api.services.payment_provider import PaddleProvider, PaymentProviderError, CheckoutRequest


def provider() -> PaddleProvider:
    return PaddleProvider(
        api_key="pdl_sdbx_apikey_test",
        webhook_secret="webhook-secret",
        environment="sandbox",
        starter_price_id="pri_starter",
        growth_price_id="pri_growth",
    )


def test_create_checkout_session_uses_transaction_api(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return httpx.Response(
            201,
            json={
                "data": {
                    "id": "txn_123",
                    "checkout": {"url": "https://checkout.example.test/?_ptxn=txn_123"},
                }
            },
        )

    monkeypatch.setattr(httpx, "request", fake_request)

    session = provider().create_checkout_session(
        CheckoutRequest(
            organization_id="org-1",
            plan_id="starter",
            customer_email="owner@example.com",
            success_url="https://app.example.test/dashboard/billing?checkout=success",
            cancel_url="https://app.example.test/dashboard/billing?checkout=cancelled",
        )
    )

    assert session.provider == "paddle"
    assert session.provider_session_id == "txn_123"
    assert session.checkout_url.endswith("txn_123")
    assert captured["url"] == "https://sandbox-api.paddle.com/transactions"
    assert captured["headers"]["Paddle-Version"] == "1"
    assert captured["json"]["items"] == [{"price_id": "pri_starter", "quantity": 1}]
    assert captured["json"]["custom_data"] == {
        "organization_id": "org-1",
        "plan_id": "starter",
    }


def test_verify_webhook_accepts_valid_signature() -> None:
    body = json.dumps(
        {
            "event_id": "evt_123",
            "event_type": "subscription.updated",
            "occurred_at": "2026-09-18T12:00:00Z",
            "data": {},
        },
        separators=(",", ":"),
    ).encode()
    timestamp = str(int(time.time()))
    digest = hmac.new(
        b"webhook-secret",
        f"{timestamp}:".encode() + body,
        hashlib.sha256,
    ).hexdigest()

    event = provider().verify_webhook(body, f"ts={timestamp};h1={digest}")

    assert event.event_id == "evt_123"
    assert event.event_type == "subscription.updated"
    assert event.payload["event_id"] == "evt_123"


def test_verify_webhook_rejects_stale_or_tampered_events() -> None:
    body = b'{"event_id":"evt_123","event_type":"subscription.updated"}'
    stale = str(int(time.time()) - 6)
    with pytest.raises(PaymentProviderError, match="Expired"):
        provider().verify_webhook(body, f"ts={stale};h1=deadbeef")

    timestamp = str(int(time.time()))
    with pytest.raises(PaymentProviderError, match="Invalid Paddle webhook signature"):
        provider().verify_webhook(body, f"ts={timestamp};h1=deadbeef")


def test_plan_mapping_is_explicit() -> None:
    paddle = provider()
    assert paddle.plan_for_price("pri_starter") == "starter"
    assert paddle.plan_for_price("pri_growth") == "growth"
    assert paddle.plan_for_price("pri_unknown") is None
