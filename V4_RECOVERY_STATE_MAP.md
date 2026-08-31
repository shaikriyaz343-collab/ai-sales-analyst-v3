# V4 Recovery State Map

## Baseline

Use the repository snapshot supplied with the handoff as the source baseline. The last known-good browser result before the failed fix cycle was **3 passed / 4 failed**. The three passing scenarios were onboarding, dataset replacement, and saved intelligence.

## Domain lifecycle

`user → organization → workspace → dataset → analysis session → scope → intelligence`

The backend owns the analytical truth. The frontend owns routing/UI state and mirrors the active dataset/session identity. Dataset replacement creates a fresh session context and invalidates stale derived intelligence.

## Explicit readiness invariants

- `data-v4-dashboard-ready="true"`: authenticated DashboardShell has completed initial app-state hydration for the active owner/workspace.
- `data-v4-dataset-ready="true"`: a current dataset and analytical session are both present in AppState.
- Browser upload helpers wait for application readiness, not merely the unchanged URL.

## Acceptance mapping

1. Onboarding: authenticated dashboard → upload → dataset/session → dataset-ready → Overview.
2. Scope: current session → selected field → `/scope-values` → value options → persisted session scope → Explore/Insights.
3. Replacement: active session → new upload → new dataset/session → stale state cleared.
4. Reports: current dataset/session → canonical report service; filename has an independently addressable DOM node.
5. Monitoring: current dataset/session → overview-derived metric → rule → deterministic evaluation.
6. Saved: current dataset/session → persisted saved item → refresh/reopen.
7. Auth lifecycle: genuinely empty browser storage → signup → dashboard → signout → public auth screen → signin → dashboard.

## Critical regression to avoid

React Hooks must be declared unconditionally before any early return. The previous attempted scope-value fix inserted a `useEffect` after authentication early-return branches, which caused the later 0/7 browser regression.

## Changes in this recovery package

- `frontend/components/dashboard-shell.tsx`: scope-value hydration hook placed before early returns; explicit readiness attributes; distinct dataset filename element.
- `e2e/tests/v4_saas_acceptance.spec.js`: behavioral assertions preserved; helper now waits on explicit app readiness; auth lifecycle uses an explicit empty storage state.

No backend analytics logic is changed by this recovery.
