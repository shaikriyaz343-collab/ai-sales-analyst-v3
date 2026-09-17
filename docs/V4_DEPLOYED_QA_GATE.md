# V4 Deployed Browser QA Gate

This release gate validates the exact deployed V4 build rather than relying on historical browser evidence.

## Preconditions

The V4 deployment must expose a public HTTPS frontend URL in the repository variable `V4_APP_URL`.

The deployed V4 FastAPI service must be reachable from the browser-test runner through the repository variable `V4_E2E_API_URL`.

Both URLs must refer to the selected production/staging V4 topology. `V4_APP_URL` must not point to the legacy Streamlit deployment.

The deployed backend must be configured according to `V4_C4F_DEPLOYMENT.md` and the final topology must satisfy `docs/V4_CROSS_SITE_AUTH_ARCHITECTURE.md`.

## Automated acceptance

The `.github/workflows/browser-qa.yml` workflow keeps the legacy browser job on `main` and uses a dedicated V4 browser job on `v4/saas-foundation`.

The V4 job uses `e2e/v4-playwright.config.js`, which runs only `v4_saas_acceptance.spec.js` and uses the dedicated V4 authentication setup. The workflow performs:

1. V4 target validation for `V4_APP_URL` and `V4_E2E_API_URL`.
2. Rejection of a legacy Streamlit target.
3. Playwright dependency installation.
4. Chromium installation.
5. V4 Playwright test-discovery validation.
6. Full V4 browser acceptance execution.
7. Artifact upload for V4 failures and reports.

The workflow may be invoked manually for an explicit release acceptance run after the V4 repository variables are configured.

## Release evidence

A release may record browser acceptance as complete only when all V4 Playwright tests pass against the exact release build and the run can be tied to the deployed commit/build identifier.

Historical 7/7 browser acceptance evidence predates the exact promoted tree and is not sufficient for final certification by itself.

## Known evidence failure mode

The previous V4-branch browser run used the legacy `APP_URL` variable, which resolved to a `streamlit.app` deployment. The workflow then ran both legacy and V4 suites against that target; the legacy tests repeatedly timed out and the job was cancelled before the V4 acceptance could complete. That run is evidence of an incorrect QA target/configuration, not evidence of a V4 application failure or pass.

The corrected workflow prevents this class of drift by requiring explicit V4 target variables and using the dedicated V4 Playwright configuration.

## Companion infrastructure gates

The release must separately record:

- Linux/container resource and capacity measurements.
- Controlled dependency-failure rehearsal.
- Restart and durable-state recovery.
- Tenant/workspace isolation verification after deployment.
- Rollback/recover-forward verification.

Passing repository CI is necessary but does not replace these deployed-environment checks.
