# AI Sales Analyst V4 — Checkpoint / Evidence / Release-Gate Matrix

Date: 2026-09-17

## Purpose

This matrix consolidates durable repository checkpoints, GitHub CI/PR evidence, deployment-state records, and the supplied historical browser conversation so already-exercised work is not repeated unnecessarily.

The rule is: **reuse valid evidence first; repair evidence linkage second; rerun an exercise only when existing evidence is invalidated, materially changed, or genuinely missing.**

A human/operator statement that an external exercise was performed is **not evidence by itself**. Such statements may identify where to look for an artifact, but they do not close a release gate unless a machine-verifiable, directly reviewable artifact can be tied to the relevant release/deployment identity.

## Release identity

> **Historical matrix note (2026-09-19):** this document is a dated checkpoint and evidence matrix. It deliberately does not act as a live pointer to the moving `v4/saas-foundation` branch head. Resolve the current candidate SHA from the live branch plus the latest successful exact-SHA release-readiness evidence. Historical SHAs in this file remain provenance.

- Production-oriented branch: `v4/saas-foundation`
- Current branch head: **resolve live from GitHub; do not use the historical value from this 2026-09-17 snapshot**
- Latest application-behavior checkpoint: `371aa5caf00308b98faeba58bf4c5736bb995b39`
- PR #29 remains a documentation-only merge, so the application-behavior checkpoint remains `371aa5caf00308b98faeba58bf4c5736bb995b39`.
- PR #28 security review is merged as `d7cbe68de3cb18c8226cb99d514b6a6624935574`; its changes are repository-side security review/tests and do not alter analytical behavior.
- The current branch head adds browser-QA workflow hardening and deployed-QA evidence documentation on top of that security-review lineage; the analytical application checkpoint remains `371aa5caf...`.
- Production target recorded in the repository: `https://peaceful-mindfulness-production-51b6.up.railway.app/`
- Deployment stack: Railway + Cloudflare R2 through the S3-compatible adapter.
- Current commit `403764...` has two successful Railway deployment statuses tied directly to the commit: service `c1446578-b14e-4ef9-b3cb-bbf3156ccb1d` deployment `d5f965e1-bd23-43ab-a07e-d3e89ec38a55`, and service `731a2cff-42db-4bc0-bc21-073d64ebfc34` deployment `78c58200-6148-4518-b28d-8d570bb6390e`.

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
| Railway/R2 evidence reconciliation | PR #26 / #27 documentation reconciliation | Complete as repository evidence-state update | Reuse as state metadata; do not treat narrative owner assertions as proof of external execution |
| Cross-site auth architecture contract | PR #29 / merge `9a9c98a...`; documentation-only | Repository contract complete | Reuse contract; production architecture verification is still open under issue #13 |
| Post-promotion security review | PR #28, merged `d7cbe68de3cb18c8226cb99d514b6a6624935574`; head `25656474...`; backend/frontend checks in run `35132271337` both successful | Complete repository-side gate | Reuse; deployment-dependent evidence remains separate |
| V4 browser-QA workflow correction | Commit `403764...`; V4 job uses dedicated `v4-playwright.config.js`, validates explicit V4 targets, and rejects legacy Streamlit targets | Complete repository QA architecture | Reuse; requires V4 deployment variables to execute acceptance |

## Product capability checkpoints

| Capability | Durable checkpoint/evidence | Status | Reuse |
|---|---|---|---|
| Organizations/auth/tenant foundation | `ORGANIZATIONS_AUTH_MILESTONE.md`; auth/session/tenant tests | Completed | Reuse |
| External PostgreSQL | C3-F rehearsal + external persistence tests | Completed application-side | Reuse; deployed provider evidence remains separate |
| S3-compatible persistence | C4-E2a external data-plane harness 6/6; S3 adapter regression 3 passed | Completed application-side | Reuse; final production-provider certification remains separate |
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

| Gate | Directly supported evidence | Evidence level | Current action |
|---|---|---|---|
| Deployed browser acceptance | Current V4 browser job `35184297215` is directly tied to commit `403764...` but failed at target validation because `V4_APP_URL` is unset and therefore ran zero browser tests. Earlier V4-branch run `35141240326` used the legacy Streamlit `APP_URL` and was cancelled after repeated timeouts. | Machine-verifiable CI result; no V4 browser acceptance executed yet | **Not certified.** Configure the real V4 frontend/API URLs, then execute the dedicated V4 browser suite; retain the resulting artifact and deployment identity. |
| R2 / dependency failure and recovery | C4-E2a real boto3-backed S3-compatible harness 6/6; repository evidence of R2 persistence/application behavior. Current Railway deployments are identified, but no machine-verifiable production outage/recovery artifact tied to those deployments was found. | Application-verified + current deployment identity; production failure/recovery exercise unverified | **Not certified.** Locate a directly reviewable production failure/recovery artifact for the relevant deployment or perform the genuinely missing exercise. |
| Linux/container resource/capacity | No raw production measurement artifact found in the reviewed repository evidence. | Unverified | **Not certified.** Obtain the actual measurement artifact or perform the required production/container measurement. |
| Tenant isolation | Auth milestone + V4 regression coverage; repository state records cross-tenant denial in the application model/tests. No deployed exact-release artifact was found that independently proves the production exercise. | Strong repository evidence; deployed certification unverified | **Repository-proven, deployment gate open.** Locate exact-release deployed verification before marking the production gate closed. |
| Restart / durable state | Execution ledger records authenticated overview reconstruction after backend restart in the accumulated evidence history. No exact-release production restart artifact was found in the reviewed repository evidence. | Repository operational evidence; deployed certification unverified | **Not production-certified.** Tie a reviewable restart/recovery artifact to the relevant Railway deployment or perform the missing exercise. |
| Rollback / recover-forward | Execution ledger records isolated rollback to a previous build and recover-forward while preserving persisted dataset state. No exact-release production rollback artifact was found in the reviewed repository evidence. | Repository evidence; deployed certification unverified | **Not production-certified.** Locate release-linked rollback evidence or perform the controlled exercise if missing. |
| Production monitoring | Runbook defines monitoring signal ownership/choreography. No measured production thresholds, observation window, alert output, or ownership artifact was found in the reviewed repository evidence. | Process documented; operational certification unverified | **Not certified.** Obtain measured monitoring/alert evidence tied to a current Railway deployment. |
| Production health/readiness | Repository records `/health` and `/ready`; execution ledger states deployed health/readiness returned 200. Current commit `403764...` has successful Railway deployment statuses with concrete deployment IDs. | Strong deployment-status evidence; endpoint result not independently bound to those exact deployment IDs | Reuse the Railway deployment IDs, but do not overstate endpoint certification without direct release-linked evidence. |
| Production object-store certification | R2 exercised through application-side S3-compatible testing; repository explicitly distinguishes this from final production-provider certification. Current Railway deployment identities are available, but no direct object-store provider run artifact was found. | Partial | **Not fully certified.** Link a directly reviewable production-provider artifact for the relevant deployment. |
| Production promotion/cutover | Current commit `403764...` has two successful Railway deployment statuses with deployment IDs; no complete release/cutover evidence package is present in the repository. | Deployment-status evidence; cutover package incomplete | Preserve the deployment IDs and add the exact cutover/release record before final approval. |

## Security / auth gate matrix

| Gate | Evidence | Status | Current action |
|---|---|---|---|
| Secure production cookie contract | `config.py`/auth tests; supplied chat shows `HttpOnly; ... SameSite=none; Secure` from a deployed response | Implemented + browser-observed historical evidence | Reuse as supporting evidence; final release linkage still matters |
| SameSite=None security invariant | Production config plus PR #28 security-contract regression, now merged; PR #28 backend/frontend checks in run `35132271337` both successful | Complete repository invariant | Reuse; deployed browser topology remains an issue #13 gate |
| CORS/trusted-host/security headers | Existing production config + PR #28 explicit contract tests; PR #28 merged with successful backend/frontend checks | Complete repository control/review gate | Reuse; production-provider behavior remains separately evidence-dependent |
| Tenant/workspace/session authorization | Auth milestone + regression coverage | Complete repository control | Reuse repository evidence; production exercise remains separately unverified |
| Object-store error redaction / 503 | PR #22 + CI | Complete | Reuse |
| Systematic post-promotion security review | PR #28 merged as `d7cbe68...`; review document + security-contract tests included | **Complete repository-side gate** | Reuse; retain deployment-dependent residual items separately |
| Cross-site domain/cookie architecture | PR #29 merged as docs-only; issue #13 remains open | Contract documented, production architecture not finally closed | Resolve selected production topology + real-browser authenticated behavior |

## Current CI / deployment evidence

### Commit `403764a2801aca7b406059e95d5baedfa1eea466`

- backend GitHub Actions job `105082925329` / run `35184297245`: **PASS**, `281 passed, 7 skipped, 2 warnings`.
- frontend GitHub Actions job `105082925657` / run `35184297245`: **PASS**.
- V4 browser job `105082934378` / run `35184297215`: **FAIL at target validation**, because `V4_APP_URL` and `V4_E2E_API_URL` are not configured; no V4 Playwright test was executed.
- legacy browser job in the same workflow: **SKIPPED** on `v4/saas-foundation`.
- Railway status `satisfied-enthusiasm - ai-sales-analyst-v3`: **success**, deployment `d5f965e1-bd23-43ab-a07e-d3e89ec38a55`, service `c1446578-b14e-4ef9-b3cb-bbf3156ccb1d`.
- Railway status `satisfied-enthusiasm - peaceful-mindfulness`: **success**, deployment `78c58200-6148-4518-b28d-8d570bb6390e`, service `731a2cff-42db-4bc0-bc21-073d64ebfc34`.

These statuses prove that both Railway deployment statuses associated with the current commit reported success. They do **not** by themselves prove browser acceptance, dependency recovery, capacity, tenant isolation, rollback, or monitoring certification.

## Historical chat evidence incorporated

The supplied partial 139-page conversation is consistent with the repository checkpoints and adds direct visual evidence for the deployed cross-site-cookie exercise:

- A browser response screenshot showed `HttpOnly; Max-Age=604800; Path=/; SameSite=none; Secure`.
- A Railway deployment screenshot showed the cross-site cookie fix deployed successfully.
- Later CI checkpoint text states commit `115fd86c3b311a0b75bf7ad9301b21dd434894c8` was green for backend regression and frontend production build.

These are supporting historical artifacts. They do not supersede the repository's requirement that final deployed Playwright certification be tied to the exact release build.

## Evidence that is safe to reuse without rerunning

The following have direct repository or CI evidence and should not be repeated merely because older documents were stale:

- decision-signal correction;
- Sharp remediation;
- object-store 503 boundary hardening;
- release/rollback runbook creation;
- repository security-review controls/tests from merged PR #28;
- repository implementation for secure cookie, CORS/trusted-host controls, tenant authorization, and object-store error handling;
- application-side PostgreSQL and S3-compatible persistence rehearsals already represented by tests/CI;
- product capability checkpoints already backed by the current application behavior tree and green CI;
- the browser-QA workflow architecture correction that separates the V4 SaaS suite from the legacy Streamlit suite.

For externally executed operational gates, **do not use owner confirmation as a reason to skip the exercise**. First locate the actual artifact and tie it to the release/deployment identity. If no suitable artifact exists, the gate remains open and the exercise may need to be repeated.

## Non-evidence leads

Previous deployment-state documents and issue comments contain owner/operator assertions that browser acceptance, R2/dependency recovery, Linux/container capacity measurement, tenant isolation, restart/recovery, monitoring, and rollback were exercised. Those assertions are retained only as **search leads** for the missing artifacts. They do not establish gate completion by themselves.

## Actual current blockers

### 1. Issue #11 — deployment evidence gates

Issue #11 remains open. The repository now has machine-verifiable Railway deployment identities for current commit `403764...`, but deployed browser acceptance did not execute because the required V4 frontend/API variables are unset. Dependency-failure/recovery, Linux/container capacity, deployed tenant-isolation verification, and release-linked restart/recovery evidence also remain unverified in the repository evidence.

### 2. Issue #12 — monitoring / rollback evidence

Issue #12 remains open. Repository choreography is documented, but measured production monitoring evidence and release-linked rollback/recover-forward evidence were not found in the reviewed repository evidence. Owner confirmation is not sufficient to close the gate.

### 3. Issue #13 — production cross-site auth architecture

PR #29 is merged and documents the topology options, but issue #13 remains open because the final frontend/API domain architecture still needs to be selected and verified in a real browser. The historical split-host Railway topology required a browser third-party-cookie exception in the cited Chrome exercise.

### 4. Issue #14 — systematic post-promotion security review

The repository-side portion is now complete: PR #28 merged as `d7cbe68...` after successful backend/frontend checks in run `35132271337`. Any remaining issue #14 work is deployment-provider evidence only.

## Recommended evidence closure sequence

1. Treat `371aa5caf...` as the application-behavior baseline and `403764...` as the current repository/release-evidence head; no analytical behavior checkpoint has changed.
2. Preserve the two successful Railway deployment identifiers attached to `403764...`.
3. Configure the actual V4 frontend and FastAPI URLs as `V4_APP_URL` and `V4_E2E_API_URL`; do not substitute the legacy Streamlit URL.
4. Execute the dedicated V4 browser acceptance suite and retain its artifact plus the Railway deployment identity.
5. Search for direct production artifacts for dependency failure/recovery, capacity, tenant isolation, restart, rollback, and monitoring; perform only the genuinely missing exercises.
6. Resolve issue #13 through final topology selection and authenticated browser verification.
7. Close issue #11/#12 only after the corresponding exact-release operational evidence is available.
8. After exact-release operational evidence and the repository/topology gates are closed, produce the final release evidence package and only then make the production-approval determination.

## Source-of-truth hierarchy

1. Current repository code/tests on `v4/saas-foundation`.
2. `V4_PROJECT_STATE.md` and `V4_PROMOTION_STATUS_2026-09-16.md` for authoritative state/release reconciliation, interpreted using the evidence-only rule in this matrix.
3. GitHub PR/CI/deployment status attached to exact commits.
4. Direct machine-verifiable deployment artifacts and measurement/test reports tied to exact releases.
5. `V4_EXECUTION_LEDGER_2026.md` for accumulated execution history.
6. C3/C4 milestone and recovery documents for detailed historical checkpoints.
7. Supplied historical chat/screenshots as supporting operational evidence where repository artifacts are unavailable.
8. Human/operator statements without corroborating artifacts are non-evidence and cannot close a gate.

## Bottom line

The repository now has a machine-verifiable current deployment identity and a corrected V4 browser-QA path. Commit `403764...` has successful backend/frontend CI and two successful Railway deployment statuses, while its dedicated V4 browser check correctly stops because the actual V4 frontend/API variables are not configured. The remaining work is therefore sharply bounded: provide the real V4 deployment endpoints, run the exact-release browser acceptance, and close the still-unverified production operational gates with direct artifacts rather than owner statements.