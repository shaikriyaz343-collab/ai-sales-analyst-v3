# AI Sales Analyst V4 — Execution Ledger

Date: 2026-09-15
Active development branch: `v4/product-development`
Production-oriented branch: `v4/saas-foundation`

## Operating rule

Development speed may change; quality gates may not.

The AI agent should perform repository engineering, testing, code generation, review and deployment orchestration wherever the available tooling permits. User interaction is reserved for product decisions, external authorization, unavailable credential entry, irreversible infrastructure approvals and final business acceptance.

## Durable baseline

- V4 SaaS foundation baseline: `3ac4b2d`
- Product development branch: `v4/product-development`
- Existing V4 foundation includes SaaS auth, organization/workspace isolation, external PostgreSQL persistence, S3-compatible object storage, deterministic analytics, monitoring/saved-intelligence surfaces, security middleware, operational metrics, concurrency protection, restart/recovery evidence and rollback/recover-forward rehearsal.
- Latest previously validated full V4 backend/regression baseline: 254 passed.
- Development CI now runs the backend regression suite and frontend production build on every push/PR to the product-development branch.

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

### Regression coverage

`tests_v4_saas/test_decision_signals.py`

- high-risk prioritization
- evidence scoring
- supported money-metric impact behavior
- empty-feed behavior
- limit semantics
- monetary/percentage display formatting

### Analyst decision feed integration

`backend/api/services/insights.py`

Validated risks/opportunities are ranked by the decision-signal layer before presentation; period-over-period changes remain secondary and evidence-backed. Ranking rationale scores are exposed as optional contract fields.

### Initial Decision Cockpit UI

- `frontend/components/decision-cockpit.tsx`
- `frontend/app/dashboard/decisions/page.tsx`

The UI presents the ranked decision feed, recommendation, evidence, ranking rationale and data-readiness findings without creating a second analytical truth source.

### Data quality promoted to a first-class contract

`backend/api/services/onboarding.py` now persists a bounded `DataQualitySummary` containing:

- quality status
- issue counts by severity
- bounded validated issue details
- affected-row counts
- deterministic recommendations

This is derived from the existing `data_quality_engine_v1.py` and does not create new thresholds or claims.

### Development CI isolation

`.github/workflows/v4-development-ci.yml`

Runs the V4 backend regression suite and frontend production build on `v4/product-development` pushes/PRs. The CI initially exposed missing pytest setup and missing FastAPI/Uvicorn runtime dependency declarations; both were corrected.

Verified development CI after those corrections:

- frontend production build: PASS
- V4 backend regression suite: PASS on run `34972038177`

## Important validation findings

The first product-CI execution caught a real TypeScript contract regression introduced by adding a new `decisions` workspace variant. The implementation was corrected by keeping the existing `Workspace` union stable and treating the Decision Cockpit route as an additive navigation item.

A later CI execution caught that `pytest` was not installed by the workflow. The workflow was corrected to install a bounded pytest 8 release.

The next execution then exposed that FastAPI was imported by the backend but absent from `requirements.txt`. FastAPI and Uvicorn are now explicit runtime dependencies.

These findings are examples of the new quality policy: every new product layer must survive automated build/test gates before it is considered a usable checkpoint.

## Railway/deployment safety finding

The previous deployment-oriented branch is coupled to the Railway production service configuration. Direct development commits there therefore risk production deployment.

The `v4/product-development` branch is now the working area for ongoing product engineering. Production promotion must be deliberate and validated.

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

The cross-site auth cookie configuration is now explicit and supports `SameSite=None` + `Secure` for the split Railway frontend/API topology. Browser verification in the tested Chrome environment still required allowing third-party cookies for the deployed frontend because browser privacy policy can otherwise block cross-site cookies.

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
6. Convert recommended actions into user-controlled workflow with observable state transitions.
7. Add recurring intelligence and high-value connectors after the CSV/XLSX activation path is measurably strong.
8. Establish automated release/promotion gates so routine product development does not require user-operated deployment steps.

## Chat-continuity rule

This ledger is intentionally stored in the repository so future chats can recover the current product/engineering state without relying on the previous conversation transcript.
