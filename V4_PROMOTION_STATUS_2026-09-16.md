# AI Sales Analyst V4 — Promotion Status

Date: 2026-09-16

## Current promoted branch

`v4/saas-foundation`

Current merged commit:

`611e0dcd5b04c337ea96927a060a3bd970b7b725`

Merge PR:

`#7` — Promote validated V4 product tree

The merged tree is `70e7c44a07e1489b9e85f988e6d2ff383ab1cc57`.

## Validation evidence

GitHub Actions run `35116226306` validated the exact promotion candidate tree before promotion.

Backend:

`275 passed, 7 skipped`

Frontend:

Production `next build` passed successfully.

The run checked out `v4/promotion-merge`, which contained the exact tree later promoted through PR #7.

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
- dependency security cleanup, including the high-severity npm audit finding observed during CI
- cleanup of Next.js multiple-lockfile/root detection warnings

## CI infrastructure note

The foundation regression workflow remains configured on `v4/saas-foundation`.

The temporary CI-only promotion validator used to prove the exact candidate tree was removed from `main` after promotion so it cannot validate a stale fixed branch in the future.

## Historical baseline

`3ac4b2d` remains the historical protected engineering baseline for the SaaS foundation. It is not the current branch checkpoint after the 2026-09-16 promotion.
