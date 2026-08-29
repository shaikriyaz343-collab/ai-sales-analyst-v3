# AI Sales Analyst V4 — Progress

## Frozen baseline
V3 main baseline: `b8b7ad5`

## Product north star
Build a monetizable SaaS **AI Revenue / Business Analyst** that turns messy business data into trusted decisions:
`Upload → Understand → Explore → Explain → Ask → Act → Report → Monitor`.

Core invariants:
- Deterministic analytics are the numeric source of truth.
- AI may interpret/explain validated results, but must not invent metrics or values.
- Every material insight/action/report claim must retain evidence and scope.
- One dataset + one analytical session + one scope must drive every workspace.
- Dataset replacement must invalidate stale derived state.

## Completed V4 milestones
- SaaS foundation + executive Overview
- Explore
- Insights
- Ask Analyst
- Actions
- Analytical Session + Scope
- V4 Playwright acceptance harness

## Current validated capabilities
Workspaces:
- Overview
- Explore
- Insights
- Ask Analyst
- Actions
- Reports (new in this milestone)

Supported business models:
- Transactional / Retail Sales
- Sales Pipeline
- Subscription / Recurring Revenue
- Services / Professional Services

## Automated validation
- Full Python suite: 90 tests passed before Reports.
- V4 report service adds 6 tests; current full suite: 96 passed.
- V4 Playwright harness covers onboarding, scope persistence, and dataset replacement; current acceptance suite previously reached 3/3 after test-harness fixes.
- Frontend production build previously passed after the session/scope checkpoint.

## Reports milestone
Reports is built as a thin composition layer over validated Overview, Insights, and Actions services for the active dataset/session scope. It does not introduce a second calculation engine.

Current report experience:
- Executive summary
- KPI cards
- What changed
- What needs attention
- Opportunities
- Recommended actions
- Evidence + active scope
- Print / Save PDF via browser print flow
- Dataset replacement consistency

## Next product work
1. Validate Reports in the browser and add it to the V4 Playwright acceptance gate.
2. Whole-product UX/integration polish.
3. Monitoring and alerts.
4. Saved intelligence.
5. Connectors and production SaaS persistence.
6. Gemini-powered interpretation behind deterministic validation.
7. Accounts, teams, auth, usage and billing.
8. Production deployment and monetization experiments.

## Important workflow rule
Do not use isolated feature patches when a feature crosses shared contracts/state. Prefer a full current-repository reconciliation, run backend tests + frontend build + browser acceptance, then create one Git checkpoint.

## Monitoring / Alerts milestone

The product now has a deterministic monitoring rule layer over the shared analytical session. Users can create metric thresholds, evaluate them against the current scope, inspect evidence-backed alert events, and remove monitors. Dataset replacement clears prior monitoring state so alerts cannot leak across datasets.

Current milestone scope is manual evaluation plus cadence metadata (`manual`, `daily`, `weekly`). Background scheduling and delivery are intentionally deferred to the SaaS infrastructure phase.
