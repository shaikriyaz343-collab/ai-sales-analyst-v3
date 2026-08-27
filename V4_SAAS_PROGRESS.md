# AI Sales Analyst V4 — SaaS Progress

## Frozen baseline
V3: `b8b7ad5` — Fix navigation UX and Q&A return rate

## Product strategy
- Approved direction: proper SaaS frontend + Python/FastAPI analytics backend.
- Ultimate goal: a polished, robust, dynamic, end-user-friendly product that businesses will pay for repeatedly.
- Streamlit V3/V4 experiments remain reference/history only; new V4 product work stays on the SaaS branch.

## Current branch/milestone
`v4/saas-foundation`

### Completed and browser-validated
- FastAPI health API.
- Real CSV/XLSX/XLS onboarding using the V3 profiler, semantic model, business-model detector, and quality engine.
- Four supported business models validated: Retail, Pipeline, Subscription, Services.
- Structured capability contract: workspaces + analytics + modules.
- Dataset replacement resets the active dataset context.
- Next.js SaaS onboarding flow.
- Executive Overview with deterministic, evidence-backed metrics.
- URL-based workspace navigation.
- Explore workspace with metric/dimension consistency, evidence, and dataset replacement fallback.
- Browser acceptance of Retail → Pipeline replacement on Explore.

### Completed and locally validated
- SaaS backend test suite: 20 passing in the reconciled source snapshot.
- Next.js production build passed previously on the same branch after the Explore type-contract repair.
- Shared API/TypeScript contracts include onboarding, semantic, Overview, Explore, and Insights response models.
- Generated artifacts are excluded from Git: `.venv-v4/`, `frontend/node_modules/`, `frontend/.next/`, `backend/runtime_data/`.

### Current feature
Insights:
- Backend endpoint: `GET /api/v1/datasets/{dataset_id}/insights`
- Deterministic, evidence-backed risk/change/opportunity feed.
- Five Insights tests pass in the reconciled source snapshot.
- Browser validation still required before the Insights milestone is committed.

## Non-negotiable engineering gates
1. Deterministic calculations own numeric truth.
2. LLMs explain validated results only.
3. UI state is separate from analytical state.
4. Shared contracts must be extended, not replaced by feature patches.
5. Every feature must pass integrated backend tests and a frontend build before browser validation.
6. Browser validation is required before a feature is considered complete.
7. Package contents must match the actual tested change set before handing files to the user.
8. Avoid one-off UI/state patches; solve problems at the architectural level.

## Next
1. Run the current frontend build against the reconciled Insights source.
2. Browser-test Insights across Retail, Pipeline, Subscription, and Services.
3. Commit Insights as a clean checkpoint.
4. Build grounded Ask Analyst experience.
5. Build Actions and Reports.
6. Add persistence/tenant boundaries, authentication, recurring intelligence, billing and connectors before production monetization.
