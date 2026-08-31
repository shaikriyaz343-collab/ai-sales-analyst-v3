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
- Reports
- Monitoring / Alerts
- Saved Intelligence

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
- Full Python regression suite: 111 passed after Saved Intelligence.
- V4 Playwright acceptance covers onboarding, scope persistence, dataset replacement, Reports, and Monitoring; the Saved Intelligence acceptance test is included in this milestone.
- Frontend production build passed for the preceding V4 milestones; the Saved Intelligence TSX source has also been syntax-validated.

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

## Saved Intelligence milestone
Saved intelligence provides reusable, session-scoped bookmarks for validated Explore analyses, Insights, and Actions. Items preserve the dataset/session, scope snapshot, metric, optional dimension, and evidence used to create them. The current Saved workspace can reopen Explore analyses and jump into Monitoring; dataset replacement deactivates prior saved items so stale intelligence never becomes current truth.

## Next product work
1. Whole-product UX/integration polish.
2. Saved intelligence expansion and recurring workflow orchestration.
3. Connectors and production SaaS persistence.
4. Gemini-powered interpretation behind deterministic validation.
5. Accounts, teams, auth, usage and billing.
6. Production deployment and monetization experiments.

## Important workflow rule
Do not use isolated feature patches when a feature crosses shared contracts/state. Prefer a full current-repository reconciliation, run backend tests + frontend build + browser acceptance, then create one Git checkpoint.

## Monitoring / Alerts milestone

The product now has a deterministic monitoring rule layer over the shared analytical session. Users can create metric thresholds, evaluate them against the current scope, inspect evidence-backed alert events, and remove monitors. Dataset replacement clears prior monitoring state so alerts cannot leak across datasets.

Current milestone scope is manual evaluation plus cadence metadata (`manual`, `daily`, `weekly`). Background scheduling and delivery are intentionally deferred to the SaaS infrastructure phase.

## Organizations + Authentication

Implemented on top of baseline `7fa0348`. The V4 application now has a tenant-first identity boundary: organization → membership → workspace → dataset → analysis session. Authentication is handled by a server-side session cookie, and customer-owned dataset/session APIs are authorization-checked before analytical work is performed.
