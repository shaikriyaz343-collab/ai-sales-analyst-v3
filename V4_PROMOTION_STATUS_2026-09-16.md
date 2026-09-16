# AI Sales Analyst V4 — Promotion Status

Date: 2026-09-16

## Current promoted branch

`v4/saas-foundation`

Current commit:

`c7092d56bf6486b03cc56e86ab60c567f8f8a487`

Promotion merge:

`#7` — Promote validated V4 product tree

Release-hardening merge:

`#8` — Release hardening: foundation CI and Next workspace root

Decision-signal correction merge:

`#17` — Restore decision signal kind semantics

The original promoted product tree was `70e7c44a07e1489b9e85f988e6d2ff383ab1cc57`. The current foundation tree includes the release-hardening changes plus the validated decision-signal correctness correction.

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

The npm install phase still reports:

`1 high severity vulnerability`

This remains an open dependency-security release gate tracked as issue #9. The current frontend lockfile pins `sharp` `0.35.3`; public advisory data identifies versions below `0.35.4` as affected. The release gate is not considered remediated until the repository lockfile is regenerated/validated with the patched dependency and `npm audit` clears or a reviewed, time-bounded exception is recorded.

## Decision-signal correctness

PR #17 (`c7092d56bf6486b03cc56e86ab60c567f8f8a487`) corrected impact scoring so the actual signal kind is passed into `_impact_score`. This prevents severity from incorrectly reclassifying a high-severity opportunity as a risk. The correction preserved the existing money-metric boost and added regression assertions for risk/opportunity scoring semantics.

PR #17 CI run `35122269894` completed successfully before merge.

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

- final deployed Playwright/browser acceptance against the promoted build
- systematic post-promotion security and tenant-isolation review
- Linux/container resource and capacity certification
- controlled real dependency-failure rehearsal
- production-grade cross-site domain/cookie architecture where practical
- measured production deployment/cutover and rollback evidence
- monitoring/alert ownership and thresholds
- dependency security cleanup; issue #9 is open for the unresolved npm audit finding
- API hardening for object-store provider failures so `PersistenceConfigurationError` is consistently surfaced as HTTP 503 rather than generic HTTP 500

## CI infrastructure

The V4 development CI workflow validates both:

- `v4/product-development`
- `v4/saas-foundation`

for pushes and pull requests, using the existing backend regression suite and frontend production build.

The temporary CI-only promotion validator used to prove the exact candidate tree was removed after promotion so it cannot validate a stale fixed branch in the future.

## Historical baseline

`3ac4b2d` remains the historical protected engineering baseline for the SaaS foundation. It is not the current branch checkpoint after the 2026-09-16 promotion and release hardening.
