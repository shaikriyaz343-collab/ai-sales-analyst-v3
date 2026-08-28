# V4 Whole-Product Integration Audit

Audit baseline: V4 `c5a052f` committed snapshot, reconciled with the implemented Overview, Explore, Insights, Ask Analyst and Actions work.

## Findings

### Solid and preserved
- FastAPI backend with V3 deterministic analytics reuse.
- Next.js frontend with route-driven workspace navigation.
- Semantic model and capability contract separation.
- Overview as the primary deterministic KPI/insight source.
- Insights reusing Overview signals.
- Actions derived from validated Overview insights and carrying source evidence.
- Ask Analyst uses validated metrics and explicit unsupported handling.

### Architectural gaps addressed in this milestone
- Added a backend-owned `AnalysisSession`.
- Added explicit persistent `ScopeState` and validated scope filters.
- Propagated session scope into Overview, Explore, Insights, Ask Analyst and Actions.
- Evidence now reports the active calculation scope.
- Dataset replacement creates a fresh session context with empty scope and cleared analysis/comparison state.
- Added scope value discovery for deterministic filter UI.
- Frontend persists only the session identifier and reloads canonical session state from the backend.
- Added an initial V4 Playwright browser safety net without modifying the legacy Streamlit browser workflow.

## Remaining product work
- More expressive scope UX (multi-select, date ranges, saved views).
- Comparison-period modeling beyond the current session placeholder.
- Report generation from the canonical session/evidence model.
- Gemini-assisted intent interpretation behind deterministic metric validation.
- Auth, organizations/workspaces, persistence, billing, usage limits, alerts, scheduling and connectors.

## Release discipline
A V4 feature is not complete until its backend tests, frontend production build, and browser acceptance all pass. Shared contracts are protected interfaces; feature changes must extend them rather than replacing them with isolated versions.
