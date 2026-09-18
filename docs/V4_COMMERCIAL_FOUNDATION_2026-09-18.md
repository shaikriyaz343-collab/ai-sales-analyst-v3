# V4 Commercial Foundation — 2026-09-18

Status: design + deterministic entitlement code + durable repository + read-only entitlement API. No payment processor is connected and no production plan enforcement is enabled by this change.

## Commercial wedge

The initial commercial model is intentionally small:

| Plan | Indicative price | Seats | Workspaces | Core usage envelope |
|---|---:|---:|---:|---|
| 14-day Trial | $0 | 2 | 1 | 3 uploads, 50 Analyst questions, 5 reports, 3 monitoring rules, 10 saved investigations |
| Starter | $49/month | 5 | 3 | 25 uploads, 500 Analyst questions, 50 reports, 10 monitoring rules, 100 saved investigations |
| Growth | $149/month | 15 | 10 | 200 uploads, 2,500 Analyst questions, 250 reports, 50 monitoring rules, 500 saved investigations |

These are starting hypotheses for product validation, not market claims. Prices and limits should be revised from actual activation, usage, willingness-to-pay and retention data.

## Commercial lifecycle

The intended lifecycle is:

1. Sign up.
2. Start a trial.
3. Upload data and reach the first evidence-backed decision.
4. Approach meaningful usage limits.
5. Present a plan upgrade at a clear value boundary.
6. Complete payment through a provider adapter.
7. Move the organization to an active paid subscription.
8. Record usage and recurring value signals.
9. Handle cancellation, failed payment and end-of-period access deterministically.

The current implementation separates plan/entitlement rules from the payment provider so a provider can be connected later without changing analytical code.

## Entitlements

The domain model currently covers:

- plan identity and display metadata
- trial and paid-plan access states
- seat and workspace limits
- feature entitlements
- usage quotas
- deterministic remaining-capacity calculations
- canceled-at-period-end behavior
- past-due and expired access states

Numeric usage is treated as a deterministic server-side input. The model does not let an LLM change quotas or infer subscription state.

## Durable commercial state

CommercialRepository provides a narrow storage boundary for organization-level subscription state and usage state.

- Local development uses a dedicated JSON document root.
- External persistence uses the existing PostgreSQL JSON-document table with a dedicated commercial namespace.
- Subscription writes are explicit.
- The entitlement GET path is side-effect free when no commercial profile exists; it represents the deterministic default trial in memory rather than silently starting a persisted trial.
- Usage writes are intentionally not wired to high-volume production routes yet; a later implementation must add concurrency-safe, period-aware meters before quotas become enforcement controls.

## Read-only entitlement API

The development branch now exposes:

GET /api/v1/commercial/entitlements

The endpoint requires normal authenticated organization access and returns:

- current commercial access state
- feature entitlements
- seat/workspace limits
- remaining quota calculations
- current usage values
- the plan catalog

It does not create checkout sessions, mutate subscription state, or accept payment details.

## Deliberate boundary

This phase does not yet:

- collect card details
- create checkout sessions
- call a payment provider API
- enforce plan limits on production analytical routes
- store payment-provider secrets
- downgrade or suspend a customer automatically
- claim that a payment integration is production-ready

Those steps require the human operator's provider/account decision and a separate implementation with webhook verification, idempotency, auditability and recovery behavior.

## Next commercial implementation slice

1. Add period-aware usage meters for the highest-value actions with a concurrency-safe persistence strategy.
2. Add a billing UI that consumes the read-only entitlement API.
3. Select and connect a payment provider.
4. Add checkout and signed webhook lifecycle.
5. Add browser acceptance for billing/trial/upgrade/cancellation flows.

Issue #33 tracks the payment-provider and checkout lifecycle.

The existing production release gates remain independent. Commercial work stays on the separate development branch until it has its own tests and browser acceptance.

## Implementation checkpoint

Validated on 2026-09-18:

- V4 Development CI passed on the latest commercial branch.
- Isolated V4 Commercial UI QA passed against a local Next.js server with mocked authenticated API responses.
- Usage telemetry is wired to successful dataset uploads, analyst questions, report generation, monitoring-rule creation, and saved-intelligence creation.
- The production usage meter uses an atomic PostgreSQL transaction model; the local implementation uses a process-local lock for development/test safety.
- The entitlement GET path remains side-effect free.
- The plan-action controls in the Billing UI are intentionally non-interactive until a payment provider is connected.

