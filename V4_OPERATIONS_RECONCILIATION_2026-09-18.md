# AI Sales Analyst V4 — Operations Reconciliation Note — 2026-09-18

## Purpose

This note records the live repository/deployment/evidence state observed before the next release-gate execution. It is an immutable historical observation, not a substitute for deployment-provider evidence.

## Observed release lineage

- Production-oriented branch: \`v4/saas-foundation\`
- Observed branch head at reconciliation start: \`2049456160302aa788404c6024fe219d6d557286\`
- Latest application-behavior checkpoint: \`371aa5caf00308b98faeba58bf4c5736bb995b39\`
- Commits after the application checkpoint reviewed during this reconciliation include release-QA/evidence hardening and runtime-persistence path corrections in \`explore.py\` and \`forecast.py\`; no analytical formula change was identified in those inspected diffs.

## Current deployed targets

- V4 frontend: \`https://peaceful-mindfulness-production-51b6.up.railway.app\`
- V4 FastAPI: \`https://ai-sales-analyst-v3-production.up.railway.app\`
- Health: \`/api/v1/health\`
- Readiness: \`/api/v1/ready\`

## Exact deployed browser evidence observed for the current head

GitHub Actions run \`35373894224\` checked out commit \`2049456160302aa788404c6024fe219d6d557286\` and completed the dedicated V4 browser suite successfully.

- V4 browser job: \`105693972580\`
- Result: 8/8 passed
- Coverage: onboarding, scope persistence, dataset replacement, executive report, monitoring, saved intelligence, deployed cross-organization tenant isolation, authentication lifecycle
- Artifact: \`v4-browser-qa-results\`
- Artifact ID: \`10559462598\`
- Artifact SHA-256: \`09df69c0a2a9d4c4efd2609eeb6a70276acac7ce348a7ca43332e2e84b5b1beb\`

Railway commit statuses attached to \`2049456...\` are successful for both the V4 frontend and FastAPI services.

## Current CI evidence

GitHub Actions run \`35373894241\` on \`2049456...\` completed successfully:

- Backend: 283 passed, 7 skipped
- Frontend production build: PASS

## Automated production observation

GitHub Actions run \`35373894306\` completed successfully against the live deployment.

Observed hard invariants:

- API health: HTTP 200, 0.183130s
- API readiness: HTTP 200, 0.169313s
- Frontend: HTTP 200, 0.292786s
- Unauthenticated workspaces request: HTTP 401, 0.146391s

Artifact:

- \`v4-production-probe\`
- Artifact ID: \`10559387409\`
- SHA-256: \`sha256:664ef1819e67328d67f8fa5f7a211a421eb055e7fcc937940f778c44aeb968dd\`

## Evidence-quality correction

The first production-probe implementation recorded the resolved frontend/API URLs correctly in each per-check \`effective_url\` field, but the top-level JSON URL fields were written as literal shell placeholders because the embedded Python heredoc was quoted.

The corrective change in this reconciliation branch reads the URLs directly from the workflow environment so the machine-readable evidence is self-consistent.

## Release-gate posture at observation time

Closed/reusable:

- Repository-side security review.
- Object-store provider-error -> HTTP 503 application contract.
- Exact deployed V4 browser acceptance for commit \`2049456...\`.
- Deployed tenant isolation through the exact browser suite.
- Backend/frontend CI for commit \`2049456...\`.
- Production health/readiness/basic authentication-boundary probe for commit \`2049456...\`.

Still requiring direct deployment evidence or an explicit production decision:

- Controlled R2/provider failure -> expected failure semantics -> restoration -> recovery.
- Linux/container CPU/memory/resource/capacity measurements on the real production workload.
- Release-linked restart and durable-state recovery.
- Release-linked rollback/recover-forward evidence.
- Sufficient production monitoring observation window and ownership record.
- Final production frontend/API topology decision under issue #13.

## Operating model

The product is intentionally operated by one human founder/operator plus the AI engineering agent. Automated CI, provider-generated deployment signals, machine-readable evidence, least-privilege credentials, reversible workflows, and explicit human approval for consequential infrastructure actions are the compensating controls for the absence of a conventional engineering/on-call team.

## Decision

Do not create additional team-dependent process as a prerequisite for launch. Close the remaining release gates with automation and targeted provider evidence, then shift the primary execution focus toward customer activation, monetization, usage/entitlement controls, and product value measurement.
