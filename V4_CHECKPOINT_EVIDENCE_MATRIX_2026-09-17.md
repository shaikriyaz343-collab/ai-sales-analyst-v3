# AI Sales Analyst V4 — Checkpoint / Evidence / Release-Gate Matrix

Date: 2026-09-17

## Purpose

This matrix consolidates durable repository checkpoints, GitHub CI/PR evidence, deployment-state records, and the supplied historical browser conversation so already-exercised work is not repeated unnecessarily.

The rule is: **reuse valid evidence first; repair evidence linkage second; rerun an exercise only when existing evidence is invalidated, materially changed, or genuinely missing.**

## Release identity

- Production-oriented branch: `v4/saas-foundation`
- Current branch head after documentation-only PR #29: `9a9c98a3df8bb2416b7eb5bd1d86ef0f13d94f75`
- Latest application-behavior checkpoint: `371aa5caf00308b98faeba58bf4c5736bb995b39`
- PR #29 is documentation-only, so the application-behavior checkpoint remains `371aa5caf00308b98faeba58bf4c5736bb995b39`.
- Production target recorded in the repository: `https://peaceful-mindfulness-production-51b6.up.railway.app/`
- Deployment stack: Railway + Cloudflare R2 through the S3-compatible adapter.

## Durable implementation / CI checkpoints

| Slice | Checkpoint / evidence | Status | Reuse decision |
|---|---|---|---|
| V4 SaaS foundation | Historical baseline `3ac4b2d` and subsequent promoted tree | Completed historical foundation | Reuse as historical provenance; do not treat as current app tree by itself |
| V4 promotion | PR #7, promoted tree `70e7c44a07e1489b9e85f988e6d2ff383ab1cc57`; CI `35116226306`: 275 passed, 7 skipped; frontend build PASS | Complete | Reuse for promotion provenance |
| Release hardening / Next workspace | PR #8; CI `35117016753`: 275 passed, 7 skipped; frontend build PASS | Complete | Reuse |
| Release / rollback runbook | PR #16; CI `35119910472`: backend PASS, frontend build PASS | Complete repository gate | Reuse; operational evidence remains separate |
| Decision-signal correctness | PR #17 / `c7092d56...`; CI `35122269894`: backend/frontend PASS | Complete | Reuse |
| Sharp remediation | PR #21 / `b49ddb224...`; `npm ci`, high-severity audit, build PASS; CI `35126146295` backend/frontend PASS | Complete | Reuse |
| Object-store API failure boundary | PR #22 / `371aa5caf...`; disposable `35126592984` targeted + full V4 suite PASS; normal `35126724910` backend/frontend PASS | Complete | Reuse |
| State reconciliation | PR #23, #24, #25; docs-only reconciliation; application checkpoint remains `371aa5caf...` | Complete | Reuse as authoritative state metadata |
| Railway/R2 evidence reconciliation | PR #26 / #27 documentation reconciliation | Complete as evidence-state update | Reuse; do not repeat external exercises solely because older docs were stale |
| Cross-site auth architecture contract | PR #29 / merge `9a9c98a3...`; documentation-only | Repository contract complete | Reuse contract; production architecture verification is still open under issue #13 |
| Post-promotion security review | PR #28 currently open, head `25656474...`, not merged | Not yet complete on foundation branch | Do not count as merged/current checkpoint until PR #28 is actually merged and validated |

## Product capability checkpoints

| Capability | Durable checkpoint/evidence | Status | Reuse |
|---|---|---|---|
| Organizations/auth/tenant foundation | `ORGANIZATIONS_AUTH_MILESTONE.md`; auth/session/tenant tests | Completed | Reuse |
| External PostgreSQL | C3-F rehearsal + external persistence tests | Completed application-side | Reuse; deployed provider evidence remains separate |
| S3-compatible persistence | C4-E2a external data-plane harness 6/6; S3 adapter regression 3 passed | Completed application-side | Reuse |
| Decision Cockpit | execution ledger + promoted product tree | Completed | Reuse |
| Structured Ask planner | execution ledger + promoted product tree | Completed | Reuse |
| Canonical evidence/source records | execution ledger + promoted product tree | Completed | Reuse |
| Forecast/scenario | execution ledger + promoted product tree | Completed | Reuse |
| Action Workflow | action-workflow CI `35004388091` ultimately green; current application checkpoint includes it | Completed | Reuse |
| Monitoring rules/due semantics | monitoring milestone + historical green checkpoint from supplied chat (`115fd86c...`) | Completed engineering slice | Reuse; this is product monitoring behavior, not production alert certification |
| Reports | report milestone + V4 Playwright acceptance mapping | Completed product capability | Reuse |
| Q&A hardening | `QNA_HARDENING.md` | Completed product hardening | Reuse |
| Browser recovery/readiness | `V4_RECOVERY_STATE_MAP.md` and browser workflow wiring | Completed repository QA preparation | Reuse |

## Deployment / operational gate matrix

| Gate | Existing evidence | Evidence level | Current action |
|---|---|---|---|
| Deployed browser acceptance | Repository records historical 7/7; supplied chat contains deployed Railway browser screenshots and the SameSite cookie header; deployment owner later confirmed deployed browser acceptance already exercised | Historical/direct screenshot + owner-confirmed, but exact release artifact linkage is incomplete | **Do not rerun merely for stale docs.** Tie existing run/artifacts to the Railway deployment/build identity before final certification |
| R2 / dependency failure and recovery | C4-E2a real boto3-backed S3-compatible harness 6/6; execution ledger and state docs record R2 persistence; owner confirms R2/dependency failure-recovery exercised | Application-verified + owner-confirmed deployed exercise; raw provider artifact not in repo | **Archive/link existing evidence.** Avoid destructive re-test unless evidence proves to be for a different release or is unavailable |
| Linux/container resource/capacity | Owner explicitly confirms deployed Linux/container measurement; repo does not contain the raw measurements | Owner-confirmed only | **Obtain/link existing measurements**; do not substitute local measurements |
| Tenant isolation | Auth milestone + V4 regression coverage; state docs record cross-tenant denial; owner confirms deployed tenant-isolation verification | Strong repository evidence + owner-confirmed deployed check | **Reuse.** Link the deployed verification artifact if needed |
| Restart / durable state | Execution ledger records authenticated overview reconstructed from persisted data after backend restart; owner confirms deployed recovery exercise | Repository operational evidence + owner-confirmed deployed check | **Reuse/link** exact deployed evidence |
| Rollback / recover-forward | Execution ledger records isolated rollback to previous build and recover-forward while preserving persisted dataset; owner confirms production rollback evidence | Repository evidence + owner-confirmed deployed exercise | **Reuse/link** existing artifact and Railway identity |
| Production monitoring | Runbook defines monitoring signal ownership/choreography; owner confirms production monitoring exercised | Repository process + owner-confirmed operational exercise | **Link measured thresholds, ownership, observation window, and evidence** |
| Production health/readiness | C4-F records `/health` and `/ready`; execution ledger says deployed health/readiness returned 200; current Railway deployment statuses are green | Strong historical/deployed evidence | Reuse and bind to current application checkpoint/deployment identity |
| Production object-store certification | R2 exercised; repository still distinguishes application S3 harness from final provider certification | Partial | Link real production/provider evidence; no automatic claim of final certification from local/injected harness |
| Production promotion/cutover | Railway status checks on current branch head are successful; deployment target is recorded | Deployment status evidence, but no complete cutover artifact package in repo | Archive deployment/build identifier with release evidence |

## Security / auth gate matrix

| Gate | Evidence | Status | Current action |
|---|---|---|---|
| Secure production cookie contract | `config.py`/auth tests; supplied chat shows `HttpOnly; ... SameSite=none; Secure` from deployed response | Implemented + browser-observed | Reuse |
| SameSite=None security invariant | PR #28 review test design + repository config contract | Implemented in code; PR #28 test file currently lives on unmerged branch | Existing application behavior is present; do not count PR #28 as merged until verified |
| CORS/trusted-host/security headers | Existing production config + V4 security tests; PR #28 adds explicit contract tests but is unmerged | Repository implementation exists; final review PR is open | Keep as review item until PR #28 is merged/validated |
| Tenant/workspace/session authorization | Auth milestone + regression coverage | Complete repository control | Reuse |
| Object-store error redaction / 503 | PR #22 + CI | Complete | Reuse |
| Systematic post-promotion security review | PR #28 | **Open / not merged** | This is a genuine current repository blocker |
| Cross-site domain/cookie architecture | PR #29 merged as docs-only; issue #13 remains open | Contract documented, production architecture not finally closed | Must resolve selected production topology + real-browser behavior; browser privacy exception remains relevant to split-host Railway topology |

## Historical chat evidence incorporated

The supplied partial 139-page conversation is consistent with the repository checkpoints and adds direct visual evidence for the deployed cross-site-cookie exercise:

- A browser response screenshot showed `HttpOnly; Max-Age=604800; Path=/; SameSite=none; Secure`.
- A Railway deployment screenshot showed the cross-site cookie fix deployed successfully.
- Later CI checkpoint text states commit `115fd86c3b311a0b75bf7ad9301b21dd434894c8` was green for backend regression and frontend production build.

These are supporting historical artifacts. They do not supersede the repository's rule that final deployed Playwright certification must be tied to the exact release build.

## What is already safe to NOT repeat

Do not repeat these merely because an older document says they were remaining:

- decision-signal correction;
- Sharp remediation;
- object-store 503 boundary hardening;
- release/rollback runbook creation;
- Railway deployment of the SameSite cookie fix;
- basic deployed browser exercise already evidenced in the prior conversation;
- R2/dependency recovery exercise already confirmed by the deployment owner;
- deployed tenant-isolation verification already confirmed by the deployment owner;
- deployed Linux/container capacity measurement already confirmed by the deployment owner;
- deployed monitoring/rollback exercise already confirmed by the deployment owner.

The remaining work is primarily **evidence-to-release linkage**, plus the two real architectural/review blockers called out below.

## Actual current blockers

### 1. Issue #11 — deployment evidence linkage

Issue #11 is still open, but its latest comment changes the nature of the work: the deployment owner says browser acceptance, R2/dependency recovery, Linux/container capacity measurement, and tenant isolation have already been exercised, and the issue should remain open only to attach/link exact-release artifacts to the Railway deployment/build identity.

### 2. Issue #12 — monitoring/rollback evidence linkage

Issue #12 is still open, but its latest comment likewise says monitoring/rollback evidence has already been exercised and the issue should now track archival/linkage of measured monitoring and rollback evidence to Railway deployment identity.

### 3. Issue #13 — production cross-site auth architecture

PR #29 is merged and documents the topology options, but issue #13 remains open because the final frontend/API domain architecture still needs to be selected and verified in a real browser. The tested split-host Railway topology required a browser third-party-cookie exception in the historical Chrome exercise.

### 4. Issue #14 — systematic post-promotion security review

PR #28 is currently **open**, not merged. Therefore its repository-side security review must not be represented as a completed foundation-branch checkpoint yet.

## Recommended evidence closure sequence

1. Treat `371aa5caf...` as the application-behavior baseline and `9a9c98a...` as the current branch head with documentation-only delta.
2. Reconcile existing external deployment artifacts to the corresponding Railway deployment/build identity instead of rerunning completed operational exercises.
3. Preserve the existing deployed-browser/R2/capacity/tenant/recovery/monitoring/rollback evidence in the final release record.
4. Complete and validate PR #28, then update the authoritative release state for issue #14.
5. Resolve issue #13 by selecting the final production frontend/API domain topology and verifying its authenticated browser behavior.
6. Only after those gates are closed, make a final production-approval determination.

## Source-of-truth hierarchy

1. Current repository code/tests on `v4/saas-foundation`.
2. `V4_PROJECT_STATE.md` and `V4_PROMOTION_STATUS_2026-09-16.md` for authoritative state/release reconciliation.
3. GitHub PR/CI/deployment status attached to exact commits.
4. `V4_EXECUTION_LEDGER_2026.md` for accumulated execution history.
5. C3/C4 milestone and recovery documents for detailed historical checkpoints.
6. Supplied historical chat/screenshots as supporting operational evidence where repository artifacts are unavailable.

## Bottom line

The project has a real checkpoint trail. The evidence should be **reconciled, not reset**. The application-behavior checkpoint is `371aa5caf...`; the current branch head is a documentation-only continuation. The deployment owner has reported that the major external exercises have already been performed. The two clear repository/architecture items still visible in the project are issue #14 (security review, with PR #28 still open) and issue #13 (final cross-site auth topology).