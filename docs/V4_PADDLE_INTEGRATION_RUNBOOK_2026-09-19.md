# Paddle Integration Runbook — 2026-09-19

## Provider decision

Paddle is the target payment provider for the first commercial launch.

Reasons:
- Paddle currently lists the United Arab Emirates (`AE`) as a supported selling country and describes its Merchant of Record model for supported transactions. Seller approval/compliance review can still require additional information.
- Paddle provides recurring subscriptions, customer portal workflows, signed webhooks, and hosted checkout.
- The integration can keep card data and most billing/tax workflow outside our application.
- Paddle sandbox and live environments are separate, with separate credentials, catalogs, notification destinations, and customer data.

Authoritative implementation references:
- https://developer.paddle.com/api-reference/about/
- https://developer.paddle.com/api-reference/transactions/create-transaction/
- https://developer.paddle.com/build/transactions/custom-data/
- https://developer.paddle.com/webhooks/about/signature-verification/
- https://developer.paddle.com/build/subscriptions/provision-access-webhooks/
- https://developer.paddle.com/api-reference/customer-portals/create-customer-portal-session/

## Current code state

The V4 branch now contains:
- a Paddle provider adapter;
- sandbox/live base URL switching;
- API-version pinning;
- customer lookup/creation before transaction checkout;
- transaction-backed checkout session creation;
- Paddle-Signature HMAC verification with timestamp protection;
- subscription webhook reconciliation;
- duplicate event protection;
- out-of-order event protection;
- organization/provider/subscription ID persistence;
- checkout and customer-portal API endpoints;
- Billing UI actions wired to the backend;
- browser QA for configured and unconfigured checkout states.

No secret is committed.

## Required environment configuration

Backend:
- V4_BILLING_PROVIDER=paddle
- V4_PADDLE_ENVIRONMENT=sandbox for testing, live for production
- V4_PADDLE_API_KEY
- V4_PADDLE_WEBHOOK_SECRET
- V4_PADDLE_STARTER_PRICE_ID
- V4_PADDLE_GROWTH_PRICE_ID

The frontend does not need the Paddle API key. The current backend checkout endpoint returns a hosted Paddle checkout URL. Paddle's current transaction documentation also requires an approved default payment link in Checkout settings before opening checkout; this is an external Paddle account configuration item, not an application secret.

## Product/catalog setup

Create two recurring monthly Paddle prices:
- Starter — $49/month
- Growth — $149/month

The live and sandbox environments are separate, so their price IDs are separate.

## Webhook destination

Configure Paddle to POST subscription lifecycle events to:

https://ai-sales-analyst-v3-production.up.railway.app/api/v1/commercial/webhook

At minimum configure:
- subscription.created
- subscription.updated
- subscription.trialing
- subscription.activated
- subscription.past_due
- subscription.paused
- subscription.resumed
- subscription.canceled

The endpoint verifies the raw request body before parsing the JSON. Paddle documents the Paddle-Signature scheme as a timestamp plus the raw body, HMAC-SHA256, with a five-second timestamp tolerance in its SDK verification guidance. Paddle also recommends using webhooks as the subscription source of truth, deduplicating on event ID, and handling out-of-order events with occurred_at.

## Paddle account prerequisites

Before testing the application checkout, complete these external Paddle prerequisites:
- create the sandbox account and catalog;
- configure/approve the default payment link required by Paddle Checkout;
- create the sandbox API key and notification destination/webhook secret;
- keep sandbox and live IDs/credentials strictly separated;
- confirm the seller account is eligible for the intended selling jurisdiction and customer markets.

## Human-only launch steps

These cannot be truthfully completed from the repository alone:

1. Create/approve the Paddle account.
2. Create sandbox products/prices.
3. Create the sandbox API key and notification-destination secret.
4. Place those secrets in Railway.
5. Configure the notification destination to the production webhook endpoint.
6. Exercise a sandbox purchase and verify subscription.created / subscription.updated reaches production.
7. Confirm the organization receives Starter/Growth access after the webhook.
8. Run the same lifecycle in the approved live account before enabling live billing.

## Important access policy

Provider events are the source of paid subscription state. Checkout completion in a browser must not directly grant paid access.

Current telemetry remains separate from quota enforcement. Do not turn on production quota consumption until payment lifecycle evidence has been exercised and reviewed.

## Recovery

Paddle webhook delivery is at-least-once. The application deduplicates event IDs and ignores older provider events based on occurred_at.

For payment recovery, the application keeps access while status is `past_due`, surfaces the customer portal, and returns to normal active state when Paddle reports `active`. Access is revoked when Paddle reports `paused` or `canceled`.

A periodic reconciliation job should be added before the paid customer population becomes material, using Paddle subscription/customer APIs to repair drift.


## Automated reconciliation

Once Paddle is enabled, configure the GitHub repository secret `V4_BILLING_RECONCILIATION_TOKEN`. The repository also contains a daily `V4 Commercial Reconciliation` workflow that calls the protected repair endpoint and fails on reconciliation errors.

Optional repository variable: `V4_BILLING_RECONCILIATION_URL` can override the production endpoint when the deployment topology changes.

The repair endpoint is disabled while billing is disabled, so enabling this workflow does not itself enable customer billing.