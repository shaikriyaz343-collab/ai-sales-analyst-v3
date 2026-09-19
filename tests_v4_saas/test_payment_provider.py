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

    calls = []

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs.get("json")
        calls.append((method, url, kwargs))
        if url.endswith("/customers"):
            if method == "GET":
                return httpx.Response(200, json={"data": []})
            return httpx.Response(201, json={"data": {"id": "ctm_456"}})
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
            customer_name="Owner Example",
        )
    )

    assert session.provider == "paddle"
    assert session.provider_session_id == "txn_123"
    assert session.checkout_url.endswith("txn_123")
    assert calls[0][0] == "GET"
    assert calls[0][1] == "https://sandbox-api.paddle.com/customers"
    assert calls[0][2]["params"] == {"email": "owner@example.com", "per_page": 1}
    assert calls[1][0] == "POST"
    assert calls[1][1] == "https://sandbox-api.paddle.com/customers"
    assert calls[1][2]["json"]["email"] == "owner@example.com"
    assert calls[1][2]["json"]["name"] == "Owner Example"
    assert calls[1][2]["json"]["custom_data"] == {"organization_id": "org-1"}
    assert calls[2][0] == "POST"
    assert calls[2][1] == "https://sandbox-api.paddle.com/transactions"
    assert captured["method"] == "POST"
    assert captured["url"] == "https://sandbox-api.paddle.com/transactions"
    assert captured["headers"]["Paddle-Version"] == "1"
    assert captured["json"]["customer_id"] == "ctm_456"
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


def test_create_checkout_session_reuses_existing_customer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == "GET" and url.endswith("/customers"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "ctm_existing",
                            "custom_data": {"organization_id": "org-2"},
                        }
                    ]
                },
            )
        if method == "POST" and url.endswith("/transactions"):
            return httpx.Response(201, json={"data": {"id": "txn_456", "checkout": {"url": "https://checkout.example.test/?_ptxn=txn_456"}}})
        raise AssertionError("Unexpected Paddle call")

    monkeypatch.setattr(httpx, "request", fake_request)

    session = provider().create_checkout_session(
        CheckoutRequest(
            organization_id="org-2",
            plan_id="growth",
            customer_email="owner@example.com",
            customer_name="Owner Example",
        )
    )

    assert session.provider_session_id == "txn_456"
    assert len(calls) == 2
    assert calls[1][2]["json"]["customer_id"] == "ctm_existing"


def test_existing_customer_must_be_linked_to_same_organization(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(method, url, **kwargs):
        if method == "GET" and url.endswith("/customers"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "ctm_other_org",
                            "custom_data": {"organization_id": "org-other"},
                        }
                    ]
                },
            )
        raise AssertionError("Unexpected Paddle call")

    monkeypatch.setattr(httpx, "request", fake_request)

    with pytest.raises(PaymentProviderError, match="another organization"):
        provider().get_or_create_customer(
            email="owner@example.com",
            name="Owner Example",
            organization_id="org-1",
        )


def test_customer_portal_can_be_scoped_to_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return httpx.Response(
            201,
            json={
                "data": {
                    "urls": {
                        "general": {
                            "overview": "https://customers.paddle.com/session/test",
                        }
                    }
                }
            },
        )

    monkeypatch.setattr(httpx, "request", fake_request)

    url = provider().get_customer_portal_url(
        "ctm_123",
        "https://app.example.test/dashboard/billing",
        subscription_id="sub_123",
    )

    assert url.endswith("/session/test")
    assert captured["method"] == "POST"
    assert captured["url"] == "https://sandbox-api.paddle.com/customers/ctm_123/portal-sessions"
    assert captured["json"] == {"subscription_ids": ["sub_123"]}
