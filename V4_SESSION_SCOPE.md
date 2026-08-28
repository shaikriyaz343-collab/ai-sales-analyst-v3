# V4 Session and Scope

## Purpose
Establish one canonical analytical session so Overview, Explore, Insights, Ask Analyst, Actions and Reports consume the same dataset and scope.

## Session authority
FastAPI owns the canonical session. The frontend stores only the session identifier and renders returned state.

## Dataset replacement
A replacement upload creates a new session context with an empty scope and no prior comparison/analysis state.

## Scope
Scope is an explicit list of validated field filters. Current V4 UI supports deterministic single-value filters; the API contract supports `in`, `not_in`, `eq`, and `neq`.

## Analytical propagation
Session scope is passed to all analytical services. Evidence reports the same scope label as the calculation.

## Browser regression
`e2e/tests/v4_saas_acceptance.spec.js` is the initial V4 browser safety net. Run it with `V4_APP_URL=http://localhost:3000 npx playwright test --config=e2e/v4-playwright.config.js`.
