# AI Sales Analyst V4 Engineering Rules

## Product north star
Build a monetizable SaaS AI Sales Analyst, not a patched dashboard.

## Non-negotiables
- Never invent numeric values. Numeric outputs must come from deterministic calculations.
- Keep UI state separate from analytical state.
- Dataset, scope, metric, query, insight, and evidence are explicit domain objects.
- Navigation must use stable application routes; widgets must not be the analytical state machine.
- New uploads must fully replace the active dataset context and invalidate derived state.
- Unsupported metrics/capabilities must be declined explicitly.
- Every material AI insight must carry evidence and source scope.
- Browser validation is required before calling UI work complete.
- Solve state/navigation problems at the architecture level; do not add one-off widget patches.

## Product references
Use proven interaction patterns from Salesforce Revenue Intelligence, HubSpot Sales/Breeze, Tableau Pulse, ThoughtSpot, Metabase, Lightdash, and WrenAI. Copy patterns, not proprietary source code, branding, or private assets.

## Preferred architecture
- Frontend: Next.js + React, proper routing and client state.
- Backend: FastAPI.
- Analytics: preserve and extract the existing V3 deterministic Python engines.
- AI: explanation/orchestration only after deterministic validation.
- SaaS-ready: tenant/workspace boundaries should be possible without a frontend rewrite.
