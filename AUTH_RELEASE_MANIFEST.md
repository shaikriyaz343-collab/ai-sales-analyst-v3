# V4 Organizations + Authentication Release Manifest

Baseline: `7fa0348` — Build V4 Saved Intelligence

## Purpose

This release adds a tenant-first identity layer to V4 without replacing the deterministic analytical engines.

## Application changes

- `backend/api/services/auth.py` — SQLite identity store, password hashing, opaque sessions, organizations, memberships, workspaces.
- `backend/api/contracts.py` — auth/organization/workspace contracts plus owner metadata on datasets/sessions.
- `backend/api/main.py` — auth lifecycle, protected API dependencies, workspace APIs, tenant checks.
- `backend/api/services/onboarding.py` — dataset ownership metadata.
- `backend/api/services/session.py` — session ownership metadata and tenant validation.
- `frontend/lib/auth.tsx` — browser auth/session context.
- `frontend/lib/api.ts` — credentialed API client and auth/workspace APIs.
- `frontend/lib/app-state.tsx` — user/workspace-scoped analytical hydration and persistence.
- `frontend/components/auth-screen.tsx` — sign-in/sign-up UI.
- `frontend/components/onboarding-screen.tsx` — workspace-aware onboarding.
- `frontend/components/dashboard-shell.tsx` — protected dashboard, workspace selector, workspace creation, sign-out.
- `frontend/app/layout.tsx` / `frontend/app/page.tsx` — auth/app-state providers and public/authorized entry flow.
- `frontend/app/globals.css` — auth/account UI styles.
- `.gitignore` — auth database/browser-state runtime paths.

## Test and browser changes

- `tests_v4_saas/test_auth_service.py`
- `tests_v4_saas/test_auth_api.py`
- `tests_v4_saas/test_report_service.py` — protected report API test updated to authenticate first.
- `e2e/v4-auth.global.setup.js` — API-driven authenticated browser state bootstrap.
- `e2e/v4-playwright.config.js` — config-relative paths anchored with `__dirname`.
- `e2e/tests/v4_saas_acceptance.spec.js` — seven authenticated product scenarios plus isolated auth lifecycle.
- `e2e/.gitignore` — local auth state and browser output.

## Validation performed in the build workspace

- Python full suite: `121 passed`
- Python `compileall`: passed
- Changed TS/TSX transpile validation: passed
- Changed JavaScript syntax validation: passed
- Auth API manual flow: signup → `/auth/me` → upload → tenant isolation → workspace creation passed.

## Environment-dependent final gate

The build workspace does not contain the project's installed Next.js/React dependencies, so the actual Windows `next build` and Chromium browser execution remain final environment gates. The release contains no new frontend package dependency.

## Explicitly excluded

No `.git`, virtual environments, `node_modules`, `.next`, runtime databases/uploads, `.auth` state, Playwright reports/results, caches, or temporary snapshots.
