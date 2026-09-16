# AI Sales Analyst V4 — Engineering Handoff

## Current branch

`v4/saas-foundation`

## Current checkpoint

The current checkpoint is the latest commit on `v4/saas-foundation`:

`c7092d56bf6486b03cc56e86ab60c567f8f8a487`

The historical pre-promotion baseline `3ac4b2d` remains useful as release evidence but is not the current branch checkpoint.

## Durable project documents

- `V4_PROJECT_STATE.md` — authoritative engineering state and release evidence
- `V4_PROMOTION_STATUS_2026-09-16.md` — promotion/reconciliation status and exact validation evidence
- `V4_C4F_DEPLOYMENT.md` — deployment topology/configuration contract
- `V4_PRODUCT_STRATEGY_2026.md` — product/market strategy and operating plan
- `V4_COMPETITIVE_AUDIT_2026-09-15.md` — September 2026 competitive and market audit
- `docs/V4_RELEASE_RUNBOOK.md` — release, rollback, monitoring, persistence-safety, and dependency-failure choreography
- `docs/V4_DEEP_AUDIT_2026-09-16.md` — deep repository audit and remaining-gate reconciliation

## Current promoted product tree

The V4 product-development tree was reconciled and promoted into `v4/saas-foundation` through PR #7.

Promoted merge commit:

`611e0dcd5b04c337ea96927a060a3bd970b7b725`

Promoted tree:

`70e7c44a07e1489b9e85f988e6d2ff383ab1cc57`

The current foundation tree adds release hardening plus PR #17's decision-signal correctness fix. The product tree includes deterministic decision signals and evidence-aware ranking, Decision Cockpit, Forecast/scenario presentation, structured Ask planning, canonical evidence with source records, user-controlled Action Workflow, monitoring schedule/due semantics, first-class data-quality summary, and associated backend/frontend tests.

## Verified CI evidence

Promotion candidate validation on exact promoted tree:

GitHub Actions run `35116226306`

- backend: `275 passed, 7 skipped`
- frontend production build: PASS

Post-promotion release-hardening CI on `v4/saas-foundation`:

GitHub Actions run `35117016753`

- backend: `275 passed, 7 skipped`
- frontend production build: PASS
- Next.js 16.3.3 production build completed successfully
- foundation push/PR coverage is part of the V4 Development CI workflow

Release-runbook PR #16 validation:

GitHub Actions run `35119910472`

- backend: PASS
- frontend production build: PASS
- documentation-only release hardening change merged after CI success

Decision-signal correction PR #17:

GitHub Actions run `35122269894`

- backend: PASS
- frontend: PASS
- merged as `c7092d56bf6486b03cc56e86ab60c567f8f8a487`

The historical deployed-browser checkpoint recorded `7 passed`, but that browser run predates the exact promoted/current foundation tree and is not treated as exact-tree acceptance evidence.

## Security / tenant-isolation model

Protected API routes require authentication and enforce organization/workspace ownership before analytical or user-state access. Datasets and sessions are checked against organization and workspace membership; session/dataset mismatches are rejected; action, monitoring, and saved-intelligence mutations require the owning analysis session; workspace creation is restricted to owner/admin roles. CORS, trusted hosts, security headers, HSTS in production, security events, and sanitized error logging are configured.

These controls are backed by the V4 auth/security regression suite. Final production approval still requires a systematic post-promotion review and deployed acceptance.

The deep audit also identified an API hardening gap: `PersistenceConfigurationError` from object-store provider failures is not currently mapped by the central exception handler, so some configured persistence outages could surface as HTTP 500 instead of HTTP 503. This remains a repository hardening item.

## Historical SaaS foundation evidence

Earlier C4-F evidence recorded real Railway deployment, external PostgreSQL, Cloudflare R2 persistence, health/readiness verification, deployed browser acceptance, restart/recovery rehearsal, isolated rollback/recover-forward rehearsal, and tenant isolation checks.

Those are historical milestone evidence, not proof that the latest foundation tree has been re-deployed and re-certified.

## Capacity / runtime posture

`V4_ANALYTICS_CONCURRENCY` remains 4. The limiter is process-local and created during FastAPI lifespan. `/health` and `/ready` remain outside the limiter. Prior local measurements do not constitute Linux/container production capacity certification.

Deferred unless measured need justifies the added architecture: Redis/distributed limiter, Celery/background jobs, process worker architecture, DataFrame caching, blanket async conversion, and Pandas chunking rewrite.

## Current release gates

This checkpoint is not final production approval.

1. Remediate the confirmed frontend dependency security finding: the current lockfile contains `sharp` 0.35.3 while patched 0.35.4 is available. Tracked in GitHub issue #9. Do not hand-edit npm integrity metadata; regenerate the lockfile with npm and validate `npm ci`, `npm audit`, and `npm run build`.
2. Run final deployed Playwright/browser acceptance against the exact current release build.
3. Complete systematic post-promotion security and tenant-isolation review.
4. Certify Linux/container resources and capacity.
5. Complete controlled real dependency-failure rehearsal without destabilizing production.
6. Validate production cross-site domain/cookie behavior where practical to reduce third-party-cookie friction.
7. Repository-side release/rollback choreography is documented in `docs/V4_RELEASE_RUNBOOK.md`; measured production monitoring thresholds, deployment execution, and final operational evidence remain open under issue #12.
8. Define production monitoring thresholds, alerts, and operational ownership from measured baselines.
9. Align `PersistenceConfigurationError` with the API's existing HTTP 503 dependency-failure contract and add an API regression test.

## Product strategy

The strategic wedge is:

> **The fastest, most trustworthy revenue decision cockpit for sales teams that already have sales data but do not want a Salesforce/RevOps implementation project.**

The product competes on time-to-decision, evidence-backed analysis, data independence, data-quality awareness, prioritized decisions, explainable forecasting, and user-controlled action loops.

## Product roadmap

Stage A — Foundation hardening: close remaining release/reliability gaps.

Stage B — Decision cockpit: ranked attention feed, material changes, concentrated pipeline risk, stalled deals/close-date pressure, stage velocity anomalies, coverage gaps, data-quality blockers, impact/urgency/evidence ranking.

Stage C — Analyst intelligence: structured question planner, deterministic analytical execution, evidence objects, explanation, trend/segmentation/contribution/funnel/velocity/cohort analysis, and forecast/scenario analysis when data suffices.

Stage D — Action system: next-best action, owner/task recommendations, follow-up drafts, manager review queues, alerts/briefs, and opt-in observable reversible automation.

Stage E — Data network advantage: Salesforce, HubSpot, Pipedrive, common CRM/export pathways, and email/calendar/meeting signals only with strong permission and privacy controls.

## Engineering operating model

Repository engineering, testing, review, and deployment orchestration should be automated wherever available tools permit. User involvement should be concentrated on product/strategy decisions, external authorization, secrets that cannot safely be delegated, irreversible/high-impact infrastructure approvals, and final business acceptance.

No manual code editing or ad-hoc patching. Changes must be deterministic/reviewable and followed by validation.

## Quality rule

> **Development speed may change; quality gates may not.**

No shortcut may knowingly reduce correctness, security, tenant isolation, data integrity, observability, test coverage, recovery, rollback capability, performance discipline, explainability, or user control over consequential actions.

## Working-tree policy

Generated/runtime artifacts remain untracked, including local object-store data, caches, Playwright output, virtual environments, `node_modules`, and `.next`. Secrets must never be checkpointed.

## Checkpoint policy

Every meaningful V4 implementation, test, configuration, or authoritative-state change must be reviewed and validated before it is committed.

C4-F / production approval requires applicable real-infrastructure evidence; passing unit/regression tests alone is insufficient.

## Last updated

2026-09-16 — reconciled after PR #17 decision-signal correction; deployment and dependency-security gates remain open.
