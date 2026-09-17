# AI Sales Analyst V4 — Current Evidence Index

Date: 2026-09-17
Branch: `v4/saas-foundation`

## Exact release identity

The current release candidate is the branch head that contains this file and `V4_CURRENT_RELEASE_CERTIFICATION_2026-09-17.md`.

Latest application-behavior checkpoint remains:

`371aa5caf00308b98faeba58bf4c5736bb995b39`

The later commits are release-QA, evidence, and test-hardening changes. The deployed tenant-isolation browser-test correction is in `ff67e2e...` and changes only the test implementation.

## Exact deployed browser evidence

Current exact-release candidate before this evidence-index refresh:

`54fd3a477d9757d5bce6668ae0fff365ba2207b0`

Workflow run: `35191301401`

V4 browser job: `105104249542`

Backend job: `105104249417`

Frontend job: `105104249578`

Result: all jobs successful; V4 Playwright suite **8 passed**.

Browser artifact:

`v4-browser-qa-results` — artifact ID `10483368852`

Artifact SHA-256:

`f384be7b8a736ce83fd692fcfb4b3176951975d4fffd67341296e0a0985888be`

The suite covered onboarding, scope persistence, dataset replacement, executive reports, monitoring, saved intelligence, deployed cross-organization tenant isolation, and authentication lifecycle.

## Deployment identity

V4 frontend:

`https://peaceful-mindfulness-production-51b6.up.railway.app`

FastAPI:

`https://ai-sales-analyst-v3-production.up.railway.app`

For commit `54fd3a477d9757d5bce6668ae0fff365ba2207b0`:

- Railway frontend service `731a2cff-42db-4bc0-bc21-073d64ebfc34`, deployment `836392b1-91e2-459d-9564-3dcdfd3e6935`, status `success`.
- Railway API service `c1446578-b14e-4ef9-b3cb-bbf3156ccb1d`, deployment `dc466119-4055-4c59-9b81-14265992b597`, status `success`.

The API liveness endpoint is `/api/v1/health`; readiness is `/api/v1/ready`.

## Current gate state

### Closed with direct/reproducible evidence

- Exact deployed V4 browser acceptance: **CLOSED** for `54fd3a4...` — 8/8 passed.
- Deployed tenant isolation: **CLOSED** through the exact 8/8 suite.
- Backend CI on the exact candidate: **PASS**.
- Frontend production build on the exact candidate: **PASS**.
- Railway deployment statuses for the exact candidate: **SUCCESS** for frontend and API.
- Repository-side post-promotion security review: **CLOSED** through merged PR #28 and its security-contract CI.
- Repository-side object-store provider-error boundary: **CLOSED**; provider failure is mapped to the intended 503/redacted error contract in application-side validation.

### Still open because direct production evidence is absent

- Controlled production R2/provider failure → HTTP 503 → recovery.
- Linux/container CPU/memory/resource and capacity measurements.
- Deployed restart plus durable-state recovery tied to the release deployment.
- Release-linked rollback/recover-forward evidence tied to the deployment identity.
- Measured production monitoring/alert output, observation window, and ownership evidence.
- Final production frontend/API topology selection record under issue #13.
- Complete production cutover/release evidence package.

## R2 evidence boundary

`V4_R2_VISUAL_EVIDENCE_2026-09-17.md` records supporting visual evidence for bucket `ai-sales-analyst-v4-prod`, prefix `v4/`, four CSV objects, `Public Access: Disabled`, Standard storage, and non-zero stored data/operation counts.

That evidence supports bucket existence, private posture, and persisted CSV presence. It does not prove outage injection, HTTP 503 during the outage, recovery after restoration, or exact deployment linkage.

## Evidence policy

Owner/operator statements are search leads only. They do not close a gate unless a machine-verifiable or directly reviewable artifact can be tied to the relevant release/deployment identity.

Historical browser runs, screenshots, and repository-side rehearsals remain supporting evidence unless they satisfy the applicable release linkage requirement.

## Issue mapping

### Issue #11 — deployed acceptance and Linux capacity

Exact deployed browser acceptance is now closed for the prior exact candidate. Remaining work is the directly evidenced production dependency-failure/recovery exercise and Linux/container capacity measurement, plus any deployment-specific restart evidence not already artifact-linked.

### Issue #12 — rollback and monitoring

The release runbook is complete on the repository side. Production measured monitoring evidence and release-linked rollback/recover-forward evidence remain open.

### Issue #13 — cross-site auth architecture

The repository contract is complete and the split-host deployment has real-browser authenticated behavior. The issue remains open until the selected production topology is explicitly recorded as the final architecture rather than inferred from the current deployment shape.

### Issue #14 — post-promotion security review

Repository-side security review is complete. Any residual work is deployment-provider evidence only.

## Required next evidence

Do not rerun already-closed application or browser checks merely because older state documents were stale. Search first for raw production artifacts. If no suitable artifact exists, perform only the missing deployment exercise and retain a reviewable record containing the release SHA, deployment IDs, timestamps, measured result, and recovery outcome.
