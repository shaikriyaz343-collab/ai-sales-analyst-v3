# AI Sales Analyst V4 — Release Control Plane

Date: 2026-09-19

## Purpose

This is the canonical operating rule for release-state reconciliation across ChatGPT sessions, GitHub, CI, Railway, and provider evidence.

## Source-of-truth hierarchy

1. **GitHub repository** is the source of truth for code and branch topology.
2. **Exact commit SHA** is the source of truth for a release candidate.
3. **GitHub Actions artifacts/checks** are the source of truth for repository-executed validation.
4. **Railway deployment status and deployment identity** are the source of truth for provider-side deployment linkage.
5. **External provider dashboards/artifacts** are the source of truth for provider-dependent production exercises.
6. Dated handoff/status documents are historical evidence and operating context; they are not a live branch-head pointer.

## Moving branch vs immutable release

`v4/saas-foundation` is a moving production-oriented branch.

A new push changes the branch SHA and creates a new candidate. Therefore:

- never use a hard-coded SHA in a dated handoff as the current branch head;
- never certify a new SHA with browser/observation evidence from another SHA;
- freeze a candidate SHA before final certification;
- tie browser acceptance, production probe, observation evidence, deployment identity, rollback evidence, and final certification to that exact SHA.

## Current application behavior baseline

The application-behavior baseline remains:

`371aa5caf00308b98faeba58bf4c5736bb995b39`

Later commits may change commercial, acquisition, monitoring, release-QA, deployment, or documentation behavior without changing that analytical baseline.

## Current release candidate resolution

At each release decision, record:

- branch: `v4/saas-foundation`
- exact candidate SHA
- successful Development CI run
- successful Browser Acceptance QA run
- successful V4 Production Probe run
- exact-SHA production observation-window result
- Railway frontend deployment identity
- Railway API deployment identity
- open/closed operational gates
- external Paddle lifecycle evidence, when billing is being activated

## No stale-state certification

When a new candidate is created, older status documents may still contain older SHAs. That is expected historical provenance, not a contradiction.

The operator/AI agent must reconcile the candidate identity from live repository state and exact artifacts before making a release claim.

## Commercial release rule

The commercial repository-side implementation includes:

- Trial / Starter / Growth plan catalog
- usage metering
- atomic quota consumption
- failed-operation quota release
- Paddle adapter
- hosted checkout
- signed/idempotent webhook handling
- customer portal
- subscription reconciliation

Production billing remains disabled until the externally authorized Paddle account/catalog/credentials and real checkout/webhook lifecycle have been exercised.

## Production certification rule

The following remain separate external gates until directly evidenced and tied to the release candidate:

- R2/provider failure → 503 → recovery
- Linux/container CPU/memory/capacity measurement
- restart/durable-state recovery
- rollback/recover-forward
- production monitoring observation and alert ownership

Passing repository CI or a deployment-success status does not close these gates by itself.

## Session handoff rule

A new ChatGPT project session should start from this file plus live GitHub state, not by copying the full prior conversation.

**Operating principle: reuse valid evidence first; update the control plane second; rerun only genuinely missing or invalidated evidence.**
