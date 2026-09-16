# AI Sales Analyst V4 — Engineering Handoff

## Current branch

`v4/saas-foundation`

## Current checkpoint

The latest application behavior checkpoint on `v4/saas-foundation` is:

`371aa5caf00308b98faeba58bf4c5736bb995b39`

Commits after this checkpoint are documentation-only state reconciliations and do not change application behavior.

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

The current foundation tree adds release hardening, PR #17's decision-signal correctness fix, PR #21's patched Sharp lockfile, and PR #22's object-store provider-failure HTTP 503 boundary. The product tree includes deterministic decision signals and evidence-aware ranking, Decision Cockpit, Forecast/scenario presentation, structured Ask planning, canonical evidence with source records, user-controlled Action Workflow, monitoring schedule/due semantics, first-class data-quality summary, and associated backend/frontend tests.

## Production deployment target

The current production application is deployed on Railway at:

`https://peaceful-mindfulness-production-51b6.up.railway.app/`

Uploaded dataset object storage uses Cloudflare R2 through the application's S3-compatible object-store adapter.

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

Sharp remediation PR #21:

GitHub Actions run `35126146295`

- backend: PASS
- frontend production build: PASS
- exact branch-level npm validation also passed `npm ci`, `npm audit --audit-level=high`, and `npm run build`
- lockfile resolves `sharp` to `0.35.4`
- merged as `b49ddb2242dd9929b900c33eea20ec31ecc6c04f`

Object-store API hardening PR #22:

Disposable validation run `35126592984`

- targeted error-handling/persistence tests: PASS
- full `tests_v4_saas` suite: PASS
- final diff-scope and whitespace checks: PASS

Foundation PR CI run `35126724910`

- backend regression suite: PASS
- frontend production build: PASS
- merged as `371aa5caf00308b98faeba58bf4c5736bb995b39`

State-reconciliation PR #23:

GitHub Actions run `35126948659`

- backend regression suite: PASS
- frontend production build: PASS
- documentation-only merge as `d8bd717edf7e402a862f58cecb94bcd3e488ca94`

Checkpoint metadata PR #24:

GitHub Actions run `35127184802`

- backend regression suite: PASS
- frontend production build: PASS
- documentation-only merge as `77f6c8c907f6b484fe067f9b75d9b24f2260b189`

The historical deployed-browser checkpoint recorded `7 passed`. That run predates the current application behavior checkpoint and is retained as historical evidence only.

## Security / tenant-isolation model

Protected API routes require authentication and enforce organization/workspace ownership before analytical or user-state access. Datasets and sessions are checked against organization and workspace membership; session/dataset mismatches are rejected; action, monitoring, and saved-intelligence mutations require the owning analysis session; workspace creation is restricted to owner/admin roles. CORS, trusted hosts, security headers, HSTS in production, security events, and sanitized error logging are configured.

These controls are backed by the V4 auth/security regression suite.

The previously identified API hardening gap is now closed: `PersistenceConfigurationError` from object-store provider failures is centrally mapped to the existing HTTP 503 dependency-failure contract, with sanitized logging and regression coverage in PR #22.

## Deployment / operational evidence reconciliation

The historical C4-F record already contains real Railway deployment, external PostgreSQL, Cloudflare R2 persistence, health/readiness verification, deployed browser acceptance, restart/recovery rehearsal, isolated rollback/recover-forward rehearsal, and tenant-isolation checks.

On 2026-09-16, the deployment owner confirmed that these deployment-level activities have already been exercised for the current production environment: deployed browser acceptance, R2/dependency failure-recovery, Linux/container resource/capacity measurement, tenant isolation, and production monitoring/rollback evidence.

This is an evidence-reconciliation update. It does not claim that this repository independently re-executed those provider operations. Existing evidence should be retained and tied to the corresponding Railway deployment/build identity where the final release record requires machine-auditable linkage.

Do not repeat destructive dependency tests solely because an old milestone document used the word `remaining`.

## Capacity / runtime posture

`V4_ANALYTICS_CONCURRENCY` remains 4. The limiter is process-local and created during FastAPI lifespan. `/health` and `/ready` remain outside the limiter.

Prior local measurements are not used as substitutes for deployment measurements. The deployment owner has separately confirmed that Linux/container resource and capacity measurements have already been exercised in the deployed environment; the detailed measurements belong with the production evidence record rather than being recreated here.

Deferred unless measured need justifies the added architecture: Redis/distributed limiter, Celery/background jobs, process worker architecture, DataFrame caching, blanket async conversion, and Pandas chunking rewrite.

## Current release gates

This is the authoritative state after deployment-evidence reconciliation. The application behavior checkpoint remains `371aa5caf00308b98faeba58bf4c5736bb995b39`.

1. Deployed browser acceptance, R2/dependency failure-recovery, Linux/container resource/capacity checks, tenant isolation, and production monitoring/rollback checks are recorded as already exercised by the deployment owner. The remaining repository task is to retain/reference their exact artifacts and deployed Railway identity where required for auditability, not to repeat the exercises.
2. Complete the separate systematic post-promotion security review under issue #14.
3. Resolve the separate production cross-site domain/cookie architecture review under issue #13.
4. Preserve measured monitoring thresholds, alert ownership, observation window, and rollback evidence in the release record.

Repository-side dependency and API hardening items previously tracked by issues #9 and #19 are remediated and merged. They are no longer outstanding repository release gates.

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

2026-09-16 — reconciled after PR #21 Sharp remediation, PR #22 object-store 503 boundary hardening, PR #23-#26 state/documentation reconciliation, and deployment-owner confirmation of the existing Railway + Cloudflare R2 operational evidence.
