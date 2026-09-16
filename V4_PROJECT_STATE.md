# AI Sales Analyst V4 — Engineering Handoff

## Current branch

`v4/saas-foundation`

## Current checkpoint

`4acc786e48a5dbe9bdc2735aaca558ce086f1035` — corrected current foundation checkpoint documentation.

This is the current promoted engineering/product checkpoint. The historical pre-promotion baseline `3ac4b2d` remains useful as release evidence but is not the current branch checkpoint.

## Durable project documents

- `V4_PROJECT_STATE.md` — authoritative engineering state and release evidence
- `V4_PROMOTION_STATUS_2026-09-16.md` — promotion/reconciliation status and exact validation evidence
- `V4_C4F_DEPLOYMENT.md` — deployment topology/configuration contract
- `V4_PRODUCT_STRATEGY_2026.md` — product/market strategy and operating plan
- `V4_COMPETITIVE_AUDIT_2026-09-15.md` — September 2026 competitive and market audit

## Current promoted product tree

The V4 product-development tree was reconciled and promoted into `v4/saas-foundation` through PR #7.

Promoted merge commit:

`611e0dcd5b04c337ea96927a060a3bd970b7b725`

Promoted tree:

`70e7c44a07e1489b9e85f988e6d2ff383ab1cc57`

The promoted tree includes:

- deterministic decision signals and evidence-aware ranking
- Decision Cockpit
- Forecast and explainable scenario presentation
- structured Ask planner
- canonical evidence with source records
- user-controlled Action Workflow
- monitoring schedule/due semantics
- first-class data-quality summary
- associated backend tests and frontend surfaces

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
- foundation push/PR coverage is now part of the V4 Development CI workflow

The historical deployed-browser checkpoint recorded `7 passed`, but that browser run predates the exact promoted tree and is not treated as exact-tree acceptance evidence.

## Security / tenant-isolation model

The API enforces authenticated organization/workspace boundaries before analytical and user-state access:

- authentication is required for protected routes
- datasets are constrained by organization and workspace membership
- analysis sessions are constrained by organization and workspace membership
- session dataset mismatches are rejected
- action/monitoring/saved-intelligence mutation routes require the owning analysis session
- workspace creation is restricted to organization owner/admin roles
- CORS is explicit and credentialed
- trusted hosts are configured
- conservative security headers are applied
- production HSTS is applied when enabled
- structured security events and sanitized error logging are present

These controls are backed by the V4 auth/security regression suite; final production approval still requires a systematic post-promotion review and deployed acceptance.

## Historical SaaS foundation evidence

The earlier C4-F baseline recorded:

- real Railway deployment
- external PostgreSQL persistence
- Cloudflare R2 object persistence
- deployed health/readiness verification
- deployed browser acceptance
- restart/recovery rehearsal
- isolated rollback/recover-forward rehearsal
- tenant isolation checks

Those are historical milestone evidence, not proof that the latest promoted tree has been re-deployed and re-certified.

## Capacity / runtime posture

`V4_ANALYTICS_CONCURRENCY` remains 4.

The limiter is process-local and created during FastAPI lifespan. `/health` and `/ready` remain outside the limiter. Prior local measurements do not constitute Linux/container production capacity certification.

Deferred unless measured need justifies the added architecture:

- Redis/distributed limiter
- Celery/background jobs
- process worker architecture
- DataFrame caching
- blanket async conversion
- Pandas chunking rewrite

## Current release gates

This checkpoint is not final production approval.

1. Identify and remediate the high-severity frontend npm audit finding observed during CI. Tracked in GitHub issue #9.
2. Run final deployed Playwright/browser acceptance against the exact release build.
3. Complete systematic post-promotion security and tenant-isolation review.
4. Certify Linux/container resources and capacity.
5. Complete controlled real dependency-failure rehearsal without destabilizing production.
6. Improve cross-site domain/cookie architecture where practical to reduce third-party-cookie friction.
7. Produce an executable rollback/release runbook and reduce ad-hoc deployment choreography.
8. Define production monitoring thresholds, alerts, and operational ownership.

## Product strategy

The strategic wedge is:

> **The fastest, most trustworthy revenue decision cockpit for sales teams that already have sales data but do not want a Salesforce/RevOps implementation project.**

The product competes on:

- time-to-decision
- evidence-backed analysis
- data independence
- data-quality awareness
- prioritized decisions rather than dashboard volume
- explainable forecasting
- user-controlled action loops

Generic AI chat, generic dashboards, KPI cards, generic risk scoring and generic next actions are not treated as differentiated features.

## Product roadmap

Stage A — Foundation hardening
- close remaining release/reliability gaps

Stage B — Decision cockpit
- ranked attention and decision feed
- material-change detection
- concentrated pipeline risk
- stalled deals / close-date pressure
- stage velocity anomalies
- coverage gaps
- data-quality blockers
- impact / urgency / evidence ranking

Stage C — Analyst intelligence
- structured question planner
- deterministic analytical execution
- evidence objects
- natural-language explanation
- trend / segmentation / contribution / funnel / velocity / cohort analysis
- forecast/scenario analysis only when data suffices

Stage D — Action system
- next-best action
- task/owner recommendation
- follow-up drafts
- manager review queues
- alerts and recurring briefs
- opt-in, observable, reversible automation

Stage E — Data network advantage
- Salesforce
- HubSpot
- Pipedrive
- common CRM/export pathways
- email/calendar/meeting signals only with strong permission and privacy controls

## Engineering operating model

Repository engineering, testing, review and deployment orchestration should be automated wherever the available tools permit. User involvement should be concentrated on product/strategy decisions, external authorization, secrets that cannot safely be delegated, irreversible/high-impact infrastructure approvals, and final business acceptance.

No manual code editing or ad-hoc patching. Changes must be deterministic/reviewable and followed by validation.

## Quality rule

> **Development speed may change; quality gates may not.**

No shortcut may knowingly reduce correctness, security, tenant isolation, data integrity, observability, test coverage, recovery, rollback capability, performance discipline, explainability, or user control over consequential actions.

## Working-tree policy

Generated/runtime artifacts must remain untracked, including local object-store data, caches, Playwright output, virtual environments, `node_modules`, and `.next`.

Secrets must never be checkpointed.

## Checkpoint policy

Every meaningful V4 implementation, test, configuration, or authoritative-state change must be reviewed and validated before it is committed.

C4-F / production approval requires applicable real-infrastructure evidence; passing unit/regression tests alone is insufficient.

## Last updated

2026-09-16 — promoted V4 state reconciled; foundation CI enabled; exact-tree promotion and post-promotion CI evidence recorded; remaining production release gates made explicit.
