# AI Sales Analyst V4 — Execution Ledger

Date: 2026-09-15
Active development branch: `v4/product-development`
Production-oriented branch: `v4/saas-foundation`

## Operating rule

Development speed may change; quality gates may not.

The AI agent should perform repository engineering, testing, code generation, review and deployment orchestration wherever the available tooling permits. User interaction is reserved for product decisions, external authorization, unavailable credential entry, irreversible infrastructure approvals and final business acceptance.

## Durable baseline

- V4 SaaS foundation baseline: `3ac4b2d`
- Current development branch was forked from the latest `v4/saas-foundation` development checkpoint before further product work.
- Existing V4 foundation includes SaaS auth, organization/workspace isolation, external PostgreSQL persistence, S3-compatible object storage, deterministic analytics, monitoring/saved-intelligence surfaces, security middleware, operational metrics, concurrency protection, restart/recovery evidence and rollback/recover-forward rehearsal.
- Latest local V4 backend/regression validation before this product-architecture phase: 254 passed.

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
- conservative impact proxy
- deterministic priority ranking
- formatted values for UI
- no fabrication / no feed-filling

### Regression coverage

`tests_v4_saas/test_decision_signals.py`

- high-risk prioritization
- evidence scoring
- empty-feed behavior
- limit semantics
- monetary/percentage display formatting

### Analyst decision feed integration

`backend/api/services/insights.py`

Validated risks/opportunities are now ranked by the decision-signal layer before presentation; period-over-period changes remain secondary and evidence-backed.

### Initial Decision Cockpit UI

- `frontend/components/decision-cockpit.tsx`
- `frontend/app/dashboard/decisions/page.tsx`

The initial UI is intentionally additive and consumes the existing validated Insights contract rather than inventing a second analytical truth source.

### Development CI isolation

`.github/workflows/v4-development-ci.yml`

Runs the V4 backend regression suite and frontend production build on `v4/product-development` pushes/PRs. This creates a safer validation path than using the production-oriented branch as the development branch.

## Important validation finding

The first CI execution caught a real TypeScript contract regression introduced by the initial navigation integration: adding a new workspace variant broke an existing exhaustive `Record<Workspace, string>` in `workspace-view.tsx`.

The change was reverted to preserve the existing navigation/workspace contract while retaining the additive Decision Cockpit route. This is an intentional example of the new quality policy: a new UX path must not destabilize existing contracts.

The latest CI run is the source of truth for the current development branch status and must reach green before the next product checkpoint.

## Railway/deployment safety finding

The previous deployment-oriented branch is coupled to the Railway production service configuration. Direct development commits there therefore risk production deployment.

The `v4/product-development` branch is now the working area for ongoing product engineering. Production promotion must be deliberate and validated.

A temporary Railway environment duplication attempt for failure rehearsal was cancelled after it stalled during environment configuration fetch; the partially created empty environment was removed. Production remained intact.

## Next engineering sequence

1. Get development CI green and verify no regressions.
2. Strengthen the Decision Cockpit UI and connect it to existing actions/explore/evidence paths.
3. Upgrade the underlying decision-signal model with measured impact/urgency inputs where the dataset actually supports them; do not invent monetary impact.
4. Rework `Ask` into a structured planner → deterministic execution → evidence architecture.
5. Add explicit data-readiness blockers to decision ranking.
6. Introduce explainable forecasting/scenario analysis only when historical coverage supports it.
7. Build user-controlled action workflows and recurring intelligence.
8. Add connectors only after measuring CSV/XLSX activation and decision value.
9. Maintain full security, isolation, persistence, recovery and release gates throughout.

## Chat-continuity rule

This ledger is intentionally stored in the repository so future chats can recover the current product/engineering state without relying on the previous conversation transcript.
