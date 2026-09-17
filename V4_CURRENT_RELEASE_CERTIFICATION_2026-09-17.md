# AI Sales Analyst V4 — Current Release Certification Record

Date: 2026-09-17
Branch: `v4/saas-foundation`

## Release identity

This file is part of the current branch release candidate. The Git commit containing this file is the exact release identity to be used for the associated V4 deployed browser acceptance run.

Latest application-behavior checkpoint:

`371aa5caf00308b98faeba58bf4c5736bb995b39`

The changes after that checkpoint are release-QA/evidence/test-hardening work. The deployed tenant-isolation browser test was corrected after its first deployed run exposed a Playwright API misuse; the correction is in `ff67e2e...` and is test-only.

## Deployed targets

Frontend:

`https://peaceful-mindfulness-production-51b6.up.railway.app`

FastAPI:

`https://ai-sales-analyst-v3-production.up.railway.app`

The deployed FastAPI health endpoint is:

`/api/v1/health`

The readiness endpoint is:

`/api/v1/ready`

## Required exact-release browser gate

The V4 browser suite must execute against the commit containing this certification record and the two deployed URLs above.

The suite covers:

- onboarding / dataset-backed workspace
- scope persistence
- dataset replacement
- executive reports
- monitoring
- saved intelligence
- deployed cross-organization tenant isolation
- authentication lifecycle

A browser run that does not check out this exact commit is supporting evidence only and does not supersede the exact-release run.

## Current production infrastructure evidence

Cloudflare R2 visual evidence recorded on 2026-09-17 shows bucket `ai-sales-analyst-v4-prod`, prefix `v4/`, four CSV objects, Public Access `Disabled`, and Standard storage class. The capture is preserved separately in `V4_R2_VISUAL_EVIDENCE_2026-09-17.md`.

Railway deployment evidence records the V4 frontend and FastAPI services as separately addressable services.

## Gate policy

Owner/operator statements are not release evidence by themselves.

Repository tests, historical browser results, screenshots, and deployment screenshots remain supporting evidence unless they are tied to the exact release/deployment identity or are explicitly classified as application-side evidence.

Production R2/provider failure-and-recovery, Linux/container capacity, restart/durable-state recovery, rollback/recover-forward, measured monitoring/alert ownership, and final cross-site topology selection remain separate gates and must not be inferred from browser acceptance.
