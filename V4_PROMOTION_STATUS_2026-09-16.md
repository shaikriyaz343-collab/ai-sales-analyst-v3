# AI Sales Analyst V4 — Promotion Status

Date: 2026-09-16

## Current promoted branch

`v4/saas-foundation`

Current merged commit:

`c946d9fb6824ec498bc40afb360847c1eb3eee3b`

Promotion merge:

`#7` — Promote validated V4 product tree

Release-hardening merge:

`#8` — Release hardening: foundation CI and Next workspace root

The original promoted product tree was `70e7c44a07e1489b9e85f988e6d2ff383ab1cc57`; the current foundation tree adds only the release-hardening workflow/configuration changes described below.

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

The CI log does not identify the package/advisory. This remains an open release gate tracked as issue #9 and must not be treated as remediated until `npm audit` identifies and clears or formally exceptions the finding.

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

## Decision-signal correctness

`backend/api/services/decision_signals.py` preserves the actual signal kind when calculating impact. Risks/attention are not reclassified as opportunities merely because of severity.

Ranking remains deterministic and consumes only validated Overview insight objects. It does not fabricate signals or numeric values.

## Remaining release gates

This promotion is an engineering/product checkpoint, not final production approval.

Remaining release work includes:

- final deployed Playwright/browser acceptance against the promoted build
- systematic post-promotion security and tenant-isolation review
- Linux/container resource and capacity certification
- controlled real dependency-failure rehearsal
- production-grade cross-site domain/cookie architecture where practical
- executable rollback runbook and release automation
- monitoring/alert ownership and thresholds
- dependency security cleanup; issue #9 is open for the unresolved npm audit finding

## CI infrastructure

The V4 development CI workflow now validates both:

- `v4/product-development`
- `v4/saas-foundation`

for pushes and pull requests, using the existing backend regression suite and frontend production build.

The temporary CI-only promotion validator used to prove the exact candidate tree was removed from `main` after promotion so it cannot validate a stale fixed branch in the future.

## Historical baseline

`3ac4b2d` remains the historical protected engineering baseline for the SaaS foundation. It is not the current branch checkpoint after the 2026-09-16 promotion and release hardening.
