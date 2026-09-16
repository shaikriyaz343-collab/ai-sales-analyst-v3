# AI Sales Analyst V4 — Promotion Status

Date: 2026-09-16

## Current promoted branch

`v4/saas-foundation`

Latest application behavior checkpoint:

`371aa5caf00308b98faeba58bf4c5736bb995b39`

Commits after this checkpoint are documentation-only state reconciliations and do not change application behavior.

Production deployment target:

`https://peaceful-mindfulness-production-51b6.up.railway.app/`

Deployment stack:

- Application hosting/deployment: Railway
- Uploaded dataset object storage: Cloudflare R2 through the S3-compatible persistence adapter

Promotion merge:

`#7` — Promote validated V4 product tree

Release-hardening merge:

`#8` — Release hardening: foundation CI and Next workspace root

Decision-signal correction merge:

`#17` — Restore decision signal kind semantics

Sharp dependency remediation merge:

`#21` — Update Sharp to patched release

Object-store API hardening merge:

`#22` — Map object-store provider failures to 503

State reconciliation merge:

`#23` — Reconcile V4 release state after security hardening

Checkpoint metadata correction merge:

`#24` — Correct V4 branch checkpoint metadata

The original promoted product tree was `70e7c44a07e1489b9e85f988e6d2ff383ab1cc57`. The current foundation tree includes the release-hardening changes plus the validated decision-signal correctness correction, patched Sharp lockfile, and object-store provider-failure API boundary.

## Promotion validation evidence

GitHub Actions run `35116226306` validated the exact promotion candidate tree before promotion.

Backend:

`275 passed, 7 skipped`

Frontend:

Production `next build` passed successfully.

The run checked out `v4/promotion-merge`, which contained the exact tree later promoted through PR #7.

## Post-promotion release-hardening validation

GitHub Actions run `35117016753` validated the exact post-merge foundation commit `c946d9fb6824ec498bc40afb360847c1eb3eee3b`.

Backend:

`275 passed, 7 skipped, 2 warnings`

Frontend:

Production `next build` passed. The build completed on Next.js `16.3.3` with the expected V4 routes, including `/dashboard`, `/dashboard/[workspace]`, `/dashboard/decisions`, and `/dashboard/forecast`.

The prior Turbopack multi-lockfile root warning is addressed by explicitly setting `turbopack.root` to the frontend workspace.

## Decision-signal correctness

PR #17 (`c7092d56bf6486b03cc56e86ab60c567f8f8a487`) corrected impact scoring so the actual signal kind is passed into `_impact_score`. This prevents severity from incorrectly reclassifying a high-severity opportunity as a risk. The correction preserved the existing money-metric boost and added regression assertions for risk/opportunity scoring semantics.

PR #17 CI run `35122269894` completed successfully before merge.

## Dependency-security remediation

PR #21 updated the npm-generated frontend lockfile so the transitive `sharp` resolution is `0.35.4`.

Branch-level validation:

- `npm ci`: PASS
- `npm audit --audit-level=high`: PASS with no high-severity findings
- `npm run build`: PASS

Normal V4 Development CI for PR #21 was run as GitHub Actions run `35126146295`:

- backend regression suite: PASS
- frontend production build: PASS

PR #21 merged as `b49ddb2242dd9929b900c33eea20ec31ecc6c04f`. Issue #9 is therefore remediated at repository level.

## Object-store API hardening

PR #22 added a central `PersistenceConfigurationError` handler that returns the existing safe HTTP 503 object-store dependency-failure response, emits `object_store_failures_total` telemetry with operation/failure classification, and preserves sanitized logging.

The disposable validation run `35126592984` passed targeted error-handling/persistence tests, the full `tests_v4_saas` suite, and exact diff-scope/whitespace checks. The normal V4 Development CI run `35126724910` passed both backend regression and frontend production build.

PR #22 merged as `371aa5caf00308b98faeba58bf4c5736bb995b39`. Issue #19 is therefore remediated at repository level.

## Promoted product work

The promoted V4 tree includes the accumulated product-development work for:

- deterministic decision signals and evidence-aware ranking
- Decision Cockpit
- Forecast and explainable scenario presentation
- structured Ask planner
- canonical evidence with source records
- user-controlled Action Workflow
- monitoring schedule/due semantics
- first-class data-quality summary
- associated backend tests and frontend surfaces

## Deployment / operational evidence reconciliation

The repository contains earlier C4-F deployment evidence for the same deployment architecture, including Railway hosting, external PostgreSQL, Cloudflare R2 persistence, health/readiness verification, deployed browser acceptance, restart/recovery rehearsal, isolated rollback/recover-forward rehearsal, and tenant-isolation checks.

On 2026-09-16, the deployment owner confirmed that the deployed V4 environment is already operating on Railway with Cloudflare R2 and that the following operational checks have already been exercised: deployed browser acceptance, R2/dependency failure-recovery, Linux/container resource/capacity measurement, tenant isolation, and production monitoring/rollback evidence.

This reconciliation exists to prevent those completed activities from being accidentally repeated merely because the release-state documents were stale. The repository does not currently contain machine-verifiable provider run identifiers or attached measurement artifacts for each external check, so this record distinguishes operator-confirmed completion from independently re-verified certification.

Where the final release process requires an auditable artifact, retain the existing deployment/monitoring evidence and tie it to the deployed Railway deployment identifier and the application behavior checkpoint before closing the corresponding gate. Do not re-run destructive dependency tests solely to repair documentation.

## Remaining release gates

This promotion is an engineering/product checkpoint, not a claim that every production artifact is independently archived in Git.

The repository-side implementation gates are complete, and the external operational checks are reported by the deployment owner as already exercised. The remaining work is evidence reconciliation rather than repeating the underlying exercises:

- attach or reference the existing exact-release browser acceptance result and deployed build/deployment identifier
- attach or reference the existing Linux/container resource and capacity measurements
- attach or reference the existing dependency-failure, restart/recovery, and rollback/recover-forward evidence
- attach or reference the existing tenant-isolation verification
- attach or reference measured production monitoring thresholds, alert ownership, and observation window
- resolve the separate production cross-site domain/cookie architecture review under issue #13
- complete the separate systematic post-promotion security review under issue #14

Repository-side dependency security and object-store API hardening are complete; deployment and operational evidence should not be re-executed solely because the historical release notes were not yet reconciled.

## CI infrastructure

The V4 development CI workflow validates both:

- `v4/product-development`
- `v4/saas-foundation`

for pushes and pull requests, using the existing backend regression suite and frontend production build.

The temporary CI-only promotion validator used to prove the exact candidate tree was removed after promotion so it cannot validate a stale fixed branch in the future.

## Historical baseline

`3ac4b2d` remains the historical protected engineering baseline for the SaaS foundation. It is not the current application checkpoint after the 2026-09-16 promotion and subsequent release hardening.
