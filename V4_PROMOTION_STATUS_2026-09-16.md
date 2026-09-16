# AI Sales Analyst V4 — Promotion Status

Date: 2026-09-17 (evidence-state revision)

## Current promoted branch

`v4/saas-foundation`

Latest application behavior checkpoint:

`371aa5caf00308b98faeba58bf4c5736bb995b39`

Current foundation branch head:

`d7cbe68de3cb18c8226cb99d514b6a6624935574`

PR #28 is merged into the foundation branch. It adds repository-side security review/test coverage only and does not change analytical behavior, so the application behavior checkpoint remains `371aa5caf00308b98faeba58bf4c5736bb995b39`.

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

State reconciliation merges:

`#23`, `#24`, `#25`, `#26`, `#27` — state/evidence/documentation reconciliation

Cross-site auth architecture contract:

`#29` — documentation-only production auth topology contract

Post-promotion security review:

`#28` — repository-side security review and explicit security-contract regression coverage; merged as `d7cbe68de3cb18c8226cb99d514b6a6624935574`

The original promoted product tree was `70e7c44a07e1489b9e85f988e6d2ff383ab1cc57`. The current foundation tree includes the release-hardening changes plus the validated decision-signal correction, patched Sharp lockfile, object-store provider-failure API boundary, cross-site auth architecture contract, evidence-only release matrix, and merged repository-side security review.

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

## Post-promotion security review

PR #28 added the repository-side systematic security review and explicit regression tests covering:

- authentication/session controls and password/session handling
- tenant/workspace authorization and cross-organization denial coverage
- production persistence boundaries
- secure cookie / SameSite invariants
- credentialed CORS allowlisting
- trusted-host restrictions
- security response headers and HSTS behavior
- sanitized error handling/logging and dependency-failure mapping

GitHub Actions run `35132271337` completed successfully for both backend and frontend on PR #28 head `25656474a2f5acba86e83ae3aba2a6b974a1cb1d`. The PR was then merged as `d7cbe68de3cb18c8226cb99d514b6a6624935574`.

This closes the repository-side portion of the systematic post-promotion security review. It does not certify production-provider behavior or the final cross-site browser topology.

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

Historical C4-F records describe Railway hosting, external PostgreSQL, Cloudflare R2 persistence, health/readiness verification, browser acceptance, restart/recovery rehearsal, isolated rollback/recover-forward rehearsal, and tenant-isolation checks. The supplied historical conversation also contains deployed screenshots and a browser-observed secure cross-site cookie header.

Previous deployment-state documents and issue comments contain owner/operator statements that additional production exercises were performed. Under the current evidence policy, **those statements are leads only and do not close release gates**.

For final certification, each external operational gate requires a directly reviewable artifact tied to the relevant release/deployment identity. Repository application-side rehearsals remain reusable but do not substitute for production evidence.

## Remaining release gates

The following production/deployment gates remain open because exact-release artifacts have not been established in the reviewed repository evidence:

- deployed browser acceptance against the exact release build
- production R2/dependency-failure and recovery evidence
- Linux/container resource/capacity measurements
- deployed tenant-isolation verification
- deployed restart/durable-state evidence tied to the release
- rollback/recover-forward evidence tied to the release
- measured production monitoring thresholds, alert ownership, and observation window
- final production object-store/provider certification
- complete release/cutover evidence package
- final cross-site frontend/API topology and authenticated browser verification under issue #13

Do not rerun a destructive operational exercise merely to repair stale prose when a valid release-linked artifact can be found. Conversely, do not mark an exercise complete merely because an owner previously said it was performed.

## CI infrastructure

The V4 development CI workflow validates both:

- `v4/product-development`
- `v4/saas-foundation`

for pushes and pull requests, using the existing backend regression suite and frontend production build.

The temporary CI-only promotion validator used to prove the exact candidate tree was removed after promotion so it cannot validate a stale fixed branch in the future.

## Historical baseline

`3ac4b2d` remains the historical protected engineering baseline for the SaaS foundation. It is not the current application checkpoint after the 2026-09-16 promotion and subsequent release hardening/security review.

## Evidence policy

Human/operator confirmation is not a release artifact. Release gates may be considered closed only when the repository contains or directly references machine-verifiable evidence that can be mapped to the corresponding release/deployment identity. Historical screenshots and chat exports are supporting evidence and must be labeled as historical unless the exact release linkage is independently established.
