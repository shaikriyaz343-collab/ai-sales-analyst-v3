# AI Sales Analyst V4 — Engineering Handoff

## Current branch

`v4/saas-foundation`

## Current checkpoint

The latest application behavior checkpoint remains:

`371aa5caf00308b98faeba58bf4c5736bb995b39`

The current branch head is `d7cbe68de3cb18c8226cb99d514b6a6624935574`. PR #28 is merged into the foundation branch and adds repository-side security review/test coverage only; it does not change analytical behavior. The latest application-behavior checkpoint therefore remains `371aa5caf00308b98faeba58bf4c5736bb995b39`.

## Durable project documents

- `V4_PROJECT_STATE.md` — authoritative engineering state and release evidence
- `V4_PROMOTION_STATUS_2026-09-16.md` — promotion/reconciliation status and exact validation evidence
- `V4_CHECKPOINT_EVIDENCE_MATRIX_2026-09-17.md` — evidence-only checkpoint and release-gate matrix
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

The current foundation tree adds release hardening, PR #17's decision-signal correctness fix, PR #21's patched Sharp lockfile, PR #22's object-store provider-failure HTTP 503 boundary, PR #29's production cross-site auth architecture contract, and PR #28's repository-side post-promotion security review/test coverage. The product tree includes deterministic decision signals and evidence-aware ranking, Decision Cockpit, Forecast/scenario presentation, structured Ask planning, canonical evidence with source records, user-controlled Action Workflow, monitoring schedule/due semantics, first-class data-quality summary, and associated backend/frontend tests.

## Production deployment target

The production target recorded by the repository is:

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

Post-promotion security review PR #28:

GitHub Actions run `35132271337`

- backend: PASS
- frontend: PASS
- review scope covers authentication/session controls, tenant/workspace authorization, persistence boundaries, CORS/trusted hosts, response security headers, error handling/logging, and explicit security-contract regressions
- merged as `d7cbe68de3cb18c8226cb99d514b6a6624935574`

The historical deployed-browser checkpoint recorded `7 passed`. That run predates the current application behavior checkpoint and is retained as historical evidence only.

## Security / tenant-isolation model

Protected API routes require authentication and enforce organization/workspace ownership before analytical or user-state access. Datasets and sessions are checked against organization and workspace membership; session/dataset mismatches are rejected; action, monitoring, and saved-intelligence mutations require the owning analysis session; workspace creation is restricted to owner/admin roles. CORS, trusted hosts, security headers, HSTS in production, security events, and sanitized error logging are configured.

These controls are backed by the V4 auth/security regression suite and the merged PR #28 security-contract tests.

The previously identified API hardening gap is closed: `PersistenceConfigurationError` from object-store provider failures is centrally mapped to the existing HTTP 503 dependency-failure contract, with sanitized logging and regression coverage in PR #22.

## Deployment / operational evidence reconciliation

Historical C4-F records describe Railway deployment, external PostgreSQL, Cloudflare R2 persistence, health/readiness verification, browser acceptance, restart/recovery rehearsal, isolated rollback/recover-forward rehearsal, and tenant-isolation checks. The supplied historical conversation also contains deployed screenshots and a browser-observed secure cross-site cookie header.

Previous deployment-state documents and issue comments additionally contain owner/operator statements that browser acceptance, R2/dependency recovery, Linux/container capacity measurement, tenant isolation, restart/recovery, monitoring, and rollback were exercised. **Those statements are non-evidence for release certification.** They are retained only as leads for locating direct artifacts.

No external gate may be marked complete here without a machine-verifiable artifact tied to the relevant deployment/release identity. Repository application-side rehearsals do not substitute for production-provider evidence.

## Capacity / runtime posture

`V4_ANALYTICS_CONCURRENCY` remains 4. The limiter is process-local and created during FastAPI lifespan. `/health` and `/ready` remain outside the limiter.

Prior local measurements are not used as substitutes for deployment measurements. No raw production Linux/container capacity measurement artifact has been established in the reviewed repository evidence.

Deferred unless measured need justifies the added architecture: Redis/distributed limiter, Celery/background jobs, process worker architecture, DataFrame caching, blanket async conversion, and Pandas chunking rewrite.

## Current release gates

This is the authoritative evidence-only state. The application behavior checkpoint remains `371aa5caf00308b98faeba58bf4c5736bb995b39`; the current foundation branch head is `d7cbe68de3cb18c8226cb99d514b6a6624935574`.

1. **Deployed browser acceptance:** historical 7/7 and deployed screenshots exist, but no exact-release Playwright artifact tied to the release identity has been established. Open.
2. **R2/dependency failure-recovery:** application-side S3-compatible rehearsal exists, but no machine-verifiable production failure/recovery artifact tied to the release has been established. Open.
3. **Linux/container capacity:** no raw production measurement artifact has been established. Open.
4. **Tenant isolation in production:** repository authorization controls are proven, but exact-release deployed verification is not independently evidenced. Open.
5. **Restart/durable state:** repository execution history contains recovery evidence, but exact-release production linkage is not established. Open.
6. **Rollback/recover-forward:** repository execution history contains rehearsal evidence, but exact-release production linkage is not established. Open.
7. **Production monitoring:** runbook/process is documented, but measured thresholds, observation window, alert output, and ownership evidence are not established. Open.
8. **Cross-site auth architecture:** PR #29 documents the choices, but issue #13 remains open until the final production topology is selected and authenticated browser behavior is verified.
9. **Repository-side post-promotion security review:** PR #28 is merged and its backend/frontend checks passed in run `35132271337`. Complete at repository level; deployment-provider residuals remain separate.

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

2026-09-17 — converted deployment-state reconciliation to an evidence-only standard and recorded merged PR #28 security review. Owner/operator statements are retained as leads only and cannot close external release gates.
