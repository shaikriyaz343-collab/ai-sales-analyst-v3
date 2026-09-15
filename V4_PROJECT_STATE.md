# AI Sales Analyst V4 — Engineering Handoff

## Current branch

`v4/saas-foundation`

## Current checkpoint

`3ac4b2d` — Fix cross-site auth cookie SameSite configuration

This is the protected engineering baseline for the current V4 work.

## Durable project documents

- `V4_PROJECT_STATE.md` — authoritative engineering state and release evidence
- `V4_C4F_DEPLOYMENT.md` — deployment topology/configuration contract
- `V4_PRODUCT_STRATEGY_2026.md` — product/market strategy and operating plan
- `V4_COMPETITIVE_AUDIT_2026-09-15.md` — September 2026 competitive and market audit

## Completed engineering phases

C4-D4a
- Request correlation
- Structured logging

C4-D4b
- Vendor-neutral operational metrics

C4-E1
- External runtime correctness
- Error boundary hardening
- Upload size enforcement
- S3 404/outage semantics
- Import-time external auth lifecycle correction

C4-E2b
- Atomic external materialization
- Unique temporary staging paths
- Concurrent download protection

C4-E2c
- Local staging before S3 upload
- Eliminated redundant S3 download after upload

C4-E2d
- Disposable bounded cache
- `V4_CACHE_MAX_BYTES`
- Recency-based eviction
- Startup orphan `.tmp` cleanup
- `V4_CACHE_MAX_BYTES >= V4_UPLOAD_MAX_BYTES` invariant

C4-E2e-1
- Analytical DataFrame loaded once
- `profile_dataframe(data)`
- `/health` converted to async
- `/ready` intentionally remains synchronous

C4-E2e-2
- `V4_ANALYTICS_CONCURRENCY=4`
- Process-local anyio `CapacityLimiter`
- Created during FastAPI lifespan
- `acquire_nowait()`
- Exhausted capacity -> HTTP 503
- `/health` and `/ready` remain outside limiter

C4-F deployment foundation
- Production FastAPI process entrypoint: `python -m backend.run_production`
- Non-reload Uvicorn process configuration
- Deployment/rehearsal contract documented in `V4_C4F_DEPLOYMENT.md`
- C4-F production-runner tests
- Real Railway deployment
- External PostgreSQL in Railway
- Cloudflare R2-backed object persistence
- Deployed health/readiness verification
- Deployed browser acceptance
- Restart/recovery rehearsal
- Rollback/recover-forward rehearsal in an isolated Railway environment

Auth hardening
- Cross-site frontend/API deployment explicitly supports configurable auth-cookie SameSite policy
- `V4_AUTH_COOKIE_SAMESITE` accepts `lax`, `strict`, or `none`
- `SameSite=None` requires secure cookies
- Deployed cross-site login verified with `SameSite=None; Secure`
- CORS credentials and explicit frontend origin verified

## Verified regression and build gates

Latest full V4 backend/regression suite:

`254 passed`

Latest focused auth suite:

`5 passed`

C4-F deployment tests:

`3 passed` in the recorded deployment-test checkpoint.

Frontend production build:

PASS

V4 Playwright browser acceptance:

`7 passed` in the recorded deployed-browser checkpoint.

`git diff --check` was clean after the latest auth-cookie fix.

## Real external persistence evidence

### Railway + PostgreSQL

Production Railway environment:

- Project: `satisfied-enthusiasm`
- Environment: `production`
- Backend service: `ai-sales-analyst-v3`
- Frontend service: `peaceful-mindfulness`
- PostgreSQL database: online

The deployed backend `/api/v1/health` and `/api/v1/ready` returned HTTP 200 during the verified production-like runs.

A disposable tenant and dataset were created through the deployed API. Authenticated Overview retrieval succeeded with deterministic values including:

- pipeline value: $300
- win rate: 100%
- open pipeline value: $200

The dataset remained readable after backend restart.

A second disposable tenant could not access the first tenant's dataset; unauthenticated dataset access returned 401; authenticated access to a nonexistent dataset returned 404.

### Cloudflare R2

The deployed object path used Cloudflare R2 with a private bucket and scoped access credentials.

Verified during the C4-F production-like rehearsal:

- dataset upload through deployed API
- object persisted in R2
- expected `v4/<dataset_id>.csv` object naming
- object readback
- durable PostgreSQL dataset metadata
- authenticated Overview rebuilt from persisted data

This is real R2 integration evidence, not merely a mocked object store.

### SeaweedFS S3-compatible rehearsal

A disposable SeaweedFS 4.46 Windows AMD64 instance was used for networked S3-compatible rehearsal.

Endpoint:

`http://127.0.0.1:8333`

Bucket:

`v4-s3-rehearsal`

Verified:

- bucket access
- object upload / HEAD / GET / DELETE
- V4 dataset upload through the real `S3ObjectStore` path
- V4 dataset retrieval through the real `S3ObjectStore` path
- object survival across storage restart
- authenticated Overview retrieval after restart
- tenant isolation remained enforced

The SeaweedFS rehearsal is supplementary compatibility evidence; it is not a substitute for the deployed Cloudflare R2 evidence.

## Rollback / recovery evidence

A disposable Railway environment was used to rehearse rollback/recover-forward without touching production.

Verified sequence:

1. deploy older protected V4 build
2. isolate backend/frontend origins for the temporary environment
3. authenticate through the isolated frontend
4. read the persisted dataset and Overview
5. recover-forward to the current build
6. verify the same persisted dataset and deterministic Overview values remained readable
7. delete the temporary Railway environment
8. remove the temporary Git worktree

Production remained untouched by the rehearsal.

## Browser / authentication caveat

The deployed frontend and API use different Railway hostnames. The backend now emits the required `SameSite=None; Secure` cookie configuration for this cross-site deployment, and the frontend sends credentialed requests.

The verified Chrome environment had third-party-cookie blocking enabled initially; authenticated browser use required a cookie-policy exception for the deployed frontend. This is an architectural deployment consideration that must be resolved before claiming frictionless browser compatibility across all user privacy configurations.

## Capacity evidence

`V4_ANALYTICS_CONCURRENCY` remains 4.

Prior E2e-3 measurements are local, single-process Windows measurements and are not production/container capacity certification.

Current evidence does not justify changing the limiter.

Explicitly deferred until measured need:

- Redis/distributed limiter
- Celery/background jobs
- process worker architecture
- DataFrame caching
- blanket async conversion
- Pandas chunking rewrite

## Current known release gaps

C4-F is not considered fully production-approved merely because the application is deployed.

Remaining gates include:

- failure rehearsal using real deployed infrastructure without destabilizing production
- systematic security/data-isolation review after the latest deployment changes
- production-grade domain/cookie architecture that avoids third-party-cookie friction where practical
- Linux/container resource and capacity certification
- automated deployment/release gates so routine releases do not depend on manual shell choreography
- final production acceptance against a clean browser/profile and representative datasets
- documented rollback runbook that is executable without ad-hoc operator inference
- monitoring/alerting thresholds and operational ownership for real production incidents

## Product direction reset — 2026-09-15

The product strategy is now governed by `V4_PRODUCT_STRATEGY_2026.md` and `V4_COMPETITIVE_AUDIT_2026-09-15.md`.

The strategic wedge is:

> **The fastest, most trustworthy revenue decision cockpit for sales teams that already have sales data but do not want a Salesforce/RevOps implementation project.**

The product must compete on:

- time-to-decision
- evidence-backed analysis
- data independence
- data-quality awareness
- prioritized decisions rather than dashboard volume
- explainable forecasting
- user-controlled action loops

Generic AI chat, generic dashboards, KPI cards, generic risk scoring and generic next actions are not treated as differentiated features.

## Product roadmap

Stage A — Foundation hardening
- close remaining release/reliability gaps

Stage B — Decision cockpit
- make Overview a ranked attention and decision feed
- material-change detection
- concentrated pipeline risk
- stalled deals / close-date pressure
- stage velocity anomalies
- coverage gaps
- data-quality blockers
- impact / urgency / evidence ranking

Stage C — Analyst intelligence
- structured question planner
- deterministic analytical execution
- evidence objects
- natural-language explanation
- trend / segmentation / contribution / funnel / velocity / cohort analysis
- forecast/scenario analysis only when data suffices

Stage D — Action system
- next-best action
- task/owner recommendation
- follow-up drafts
- manager review queues
- alerts and recurring briefs
- opt-in, observable, reversible automation

Stage E — Data network advantage
- Salesforce
- HubSpot
- Pipedrive
- common CRM/export pathways
- email/calendar/meeting signals only with strong permission and privacy controls

## Engineering operating model

The AI agent should perform as much repository engineering, testing, review and deployment orchestration as the available tools permit.

User involvement should be concentrated on product/strategy decisions, external authorization, secrets that cannot safely be delegated, irreversible/high-impact infrastructure approvals and final business acceptance.

No manual code editing and no ad-hoc patching. Changes must be deterministic/reviewable, followed by validation.

## Quality rule

> **Development speed may change; quality gates may not.**

No shortcut may knowingly reduce:

- correctness
- security
- tenant isolation
- data integrity
- observability
- test coverage
- recovery
- rollback capability
- performance discipline
- explainability
- user control over consequential actions

## Next execution order

1. Build the authoritative analytical decision-signal/evidence model.
2. Apply it without breaking current Overview/Insights/Ask/Actions contracts.
3. Upgrade Overview into the decision cockpit.
4. Strengthen Ask into planner → deterministic execution → evidence → explanation.
5. Add supported forecast/scenario analysis.
6. Close action-loop gaps.
7. Improve deployment automation and final release gates.
8. Add connectors according to measured time-to-decision value.

## Current working-tree policy

Intentionally untracked local instruction files:

- `frontend/AGENTS.md`
- `frontend/CLAUDE.md`

Generated/runtime artifacts must remain untracked, including local object-store data, caches, Playwright output, virtual environments, `node_modules`, and `.next`.

Secrets must never be checkpointed.

## Checkpoint policy

Every meaningful V4 implementation, test, configuration, or authoritative-state change must be reviewed and validated before it is committed.

C4-F / production approval requires applicable real-infrastructure evidence; passing unit/regression tests alone is insufficient.

## Last updated

2026-09-15 — authoritative state reconciled to current `3ac4b2d` checkpoint and September 2026 product strategy reset.
