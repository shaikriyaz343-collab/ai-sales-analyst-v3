# AI Sales Analyst V4 — Promotion Status

Date: 2026-09-16

## Current promoted branch

`v4/saas-foundation`

Current branch commit:

`d8bd717edf7e402a862f58cecb94bcd3e488ca94`

Latest application behavior checkpoint:

`371aa5caf00308b98faeba58bf4c5736bb995b39`

PR #23 was documentation-only and reconciled the authoritative state files after the security hardening changes; it does not change application behavior.

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

## Remaining release gates

This promotion is an engineering/product checkpoint, not final production approval.

Remaining release work includes:

- final deployed Playwright/browser acceptance against the current release build
- systematic post-promotion security and tenant-isolation review
- Linux/container resource and capacity certification
- controlled real dependency-failure rehearsal
- production-grade cross-site domain/cookie architecture where practical
- measured production deployment/cutover and rollback evidence
- monitoring/alert ownership and thresholds

Repository-side dependency security and object-store API hardening are complete; deployment and operational evidence remain separate gates.

## CI infrastructure

The V4 development CI workflow validates both:

- `v4/product-development`
- `v4/saas-foundation`

for pushes and pull requests, using the existing backend regression suite and frontend production build.

The temporary CI-only promotion validator used to prove the exact candidate tree was removed after promotion so it cannot validate a stale fixed branch in the future.

## Historical baseline

`3ac4b2d` remains the historical protected engineering baseline for the SaaS foundation. It is not the current branch checkpoint after the 2026-09-16 promotion and subsequent release hardening.
