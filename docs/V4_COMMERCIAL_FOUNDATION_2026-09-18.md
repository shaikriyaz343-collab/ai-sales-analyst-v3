# V4 Commercial Foundation — 2026-09-18

Status: design + deterministic entitlement code only. No payment processor is connected and no production plan enforcement is enabled by this change.

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

The first implementation separates the plan/entitlement rules from the payment provider so Stripe or another provider can be connected later without changing analytical code.

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

## Deliberate boundary

This phase does **not** yet:

- collect card details
- create checkout sessions
- call Stripe APIs
- enforce limits on production routes
- store payment-provider secrets
- downgrade or suspend a customer automatically
- claim that a payment integration is production-ready

Those steps require the human operator's provider/account decision and a separate implementation with webhook verification, idempotency, auditability and recovery behavior.

## Next commercial implementation slice

The next safe slice is a durable organization-level commercial repository plus read-only entitlement API. After that, usage meters can be wired to the highest-value user actions, followed by a payment-provider adapter and checkout lifecycle.

The existing production release gates remain independent. Commercial work stays on a separate development branch until it has its own tests and browser acceptance.
