# AI Sales Analyst V4 — Execution Ledger

Date: 2026-09-16
Active development branch: `v4/product-development`
Production-oriented branch: `v4/saas-foundation`

## Operating rule

Development speed may change; quality gates may not.

The AI agent should perform repository engineering, testing, code generation, review and deployment orchestration wherever the available tooling permits. User interaction is reserved for product decisions, external authorization, unavailable credential entry, irreversible infrastructure approvals and final business acceptance.

## Durable baseline

- V4 SaaS foundation baseline: `3ac4b2d`
- Product development branch: `v4/product-development`
- Existing V4 foundation includes SaaS auth, organization/workspace isolation, external PostgreSQL persistence, S3-compatible object storage, deterministic analytics, monitoring/saved-intelligence surfaces, security middleware, operational metrics, concurrency protection, restart/recovery evidence and rollback/recover-forward rehearsal.
- Development CI runs the V4 backend regression suite and frontend production build on every push/PR to the product-development branch.

## Product strategy reset

The product is being optimized for the gap between spreadsheets and heavyweight CRM/revenue-intelligence implementations.

Core promise:

`What changed → why → what is likely to happen → what needs attention → what should I do next`, with evidence for important conclusions.

Primary wedge:

- speed-to-value
- data independence
- evidence-first analysis
- decision prioritization
- data-quality awareness
- action-oriented workflow

## Work completed in this phase

### Durable product strategy

`V4_PRODUCT_STRATEGY_2026.md` defines the competitive position, target customer, differentiation roadmap, trust contract, north-star metric and operating model.

### Decision prioritization foundation

`backend/api/services/decision_signals.py`

- deterministic `DecisionSignal`
- evidence scoring
- conservative urgency scoring
- evidence-aware impact scoring for supported commercial value metrics
- deterministic priority ranking
- formatted values for UI
- no fabrication / no feed-filling

### Data quality promoted to a first-class contract

`backend/api/services/onboarding.py` persists a bounded `DataQualitySummary` containing quality status, issue counts by severity, bounded validated issue details, affected-row counts and deterministic recommendations.

### Development CI isolation

`.github/workflows/v4-development-ci.yml` runs the V4 backend regression suite and frontend production build on `v4/product-development` pushes/PRs. The workflow now installs its required pytest 8 and backend FastAPI/Uvicorn dependencies explicitly.

### Analyst decision feed and Decision Cockpit

Validated risks/opportunities are ranked by the decision-signal layer before presentation; the Decision Cockpit presents the ranking rationale, recommendation, evidence and data-readiness findings without creating a second analytical truth source.

### Structured Analyst planner

The Ask workflow carries an analytical plan alongside deterministic execution and evidence so supported questions can expose intent/metric/dimension/direction decisions without treating free-form model output as the numeric truth source.

### Canonical evidence and forecast source records

The `Evidence`/`AskEvidence` contracts support `source_fields` and `source_records`. Forecast evidence now resolves stable pipeline record identifiers when available and exposes month-specific contributing records in the UI. Explainable forecast/scenario analysis remains explicitly illustrative when it uses a user-selected uplift rather than a learned probability change.

### User-controlled action workflow

Actions are derived from validated insights, then exposed as persistent session-scoped workflow items with observable status transitions (`open`, `in_progress`, `done`, `blocked`). Status updates are protected by the same authenticated organization/workspace/session context and do not alter analytical evidence.

## Validation checkpoints

- Earlier full V4 regression baseline: 254 passed.
- Forecast source-record checkpoint and illustrative scenario UI passed development CI.
- Temporary integration regression in `main.py` was caught by CI as a missing `require_analysis_capacity` name; the API safety layer was restored before proceeding.
- Latest action-workflow CI run `35004388091` / run #65 on the action workflow integration was ultimately green: frontend production build PASS and V4 backend regression suite PASS.

The quality policy remains: no capability is treated as a durable product checkpoint until automated build/test validation passes.

## Railway/deployment safety finding

The previous deployment-oriented branch is coupled to the Railway production service configuration. Direct development commits there therefore risk production deployment.

The `v4/product-development` branch is the working area for ongoing product engineering. Production promotion must be deliberate and validated.

A temporary Railway environment duplication attempt for failure rehearsal was cancelled after it stalled during environment configuration fetch; the partially created empty environment was removed. Production remained intact.

## C4-F production evidence retained from the foundation branch

Production-like Railway evidence already established:

- deployed FastAPI health/readiness endpoints returned 200
- frontend public endpoint returned 200
- external PostgreSQL persistence was exercised
- Cloudflare R2 persistence was exercised with real boto3-backed object storage
- authenticated overview rebuilt from persisted data after backend restart
- cross-tenant dataset access was denied
- unauthenticated and missing-dataset access returned expected 401/404 semantics
- isolated rollback to the previous build and recover-forward to the current build preserved persisted dataset state

The cross-site auth cookie configuration is explicit and supports `SameSite=None` + `Secure` for the split Railway frontend/API topology. Browser verification in the tested Chrome environment still required allowing third-party cookies for the deployed frontend because browser privacy policy can otherwise block cross-site cookies.

## Remaining release gates

Do not label the product production-approved until the applicable real-infrastructure gates are satisfied:

- controlled real dependency-failure rehearsal
- final production security/configuration review
- final deployed Playwright acceptance on the exact release build
- durable restart/recovery verification on the final deployed build
- production capacity/resource evidence for the target hosting plan
- explicit production promotion procedure
- real production object-store/provider certification beyond the local S3-compatible rehearsal

## Explicitly deferred

- Redis/distributed limiter
- Celery/background jobs
- process worker architecture
- DataFrame caching
- blanket async conversion
- Pandas chunking rewrite

These are not required merely to establish the current product and deployment contract.

## Next engineering sequence

1. Complete the controlled C4-F failure/release rehearsal using a safe isolated method; do not mutate production to simulate outages.
2. Strengthen Decision Cockpit impact/urgency using only validated dataset properties and add data-quality blockers where supported.
3. Build the structured Analyst planner: intent → analytical plan → deterministic execution → evidence object → explanation.
4. Expand the canonical evidence model so important answers can cite source records as well as source fields.
5. Add explainable forecast/scenario analysis only where historical coverage and data quality justify it.
6. Convert recommended actions into user-controlled workflow with observable state transitions. **Completed on `v4/product-development`.**
7. Add recurring intelligence and high-value connectors after the CSV/XLSX activation path is measurably strong.
8. Establish automated release/promotion gates so routine product development does not require user-operated deployment steps.

## Current checkpoint

The development branch now has a validated Decision Cockpit → evidence-backed forecast → source-record traceability → user-controlled action workflow path. The next product slice should extend the intelligence loop without weakening the deterministic evidence contract or the deployment safety boundary.

## Chat-continuity rule

This ledger is intentionally stored in the repository so future chats can recover the current product/engineering state without relying on the previous conversation transcript.
