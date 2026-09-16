# V4 Deployed Browser QA Gate

This release gate validates the exact deployed V4 build rather than relying on historical browser evidence.

## Preconditions

The deployment must expose a public HTTPS frontend URL in the repository variable `APP_URL`.

The deployed backend must be reachable from that frontend and configured according to `V4_C4F_DEPLOYMENT.md`.

## Automated acceptance

Use the existing `.github/workflows/browser-qa.yml` workflow with `APP_URL` configured. The workflow performs:

1. Playwright dependency installation.
2. Chromium installation.
3. Test discovery validation.
4. Full browser acceptance execution.
5. Artifact upload for failures and reports.

The workflow may be invoked manually for an explicit release acceptance run.

## Release evidence

A release may record browser acceptance as complete only when all Playwright tests pass against the exact release build and the run can be tied to the deployed commit/build identifier.

Historical 7/7 browser acceptance evidence predates the exact promoted tree and is not sufficient for final certification by itself.

## Companion infrastructure gates

The release must separately record:

- Linux/container resource and capacity measurements.
- Controlled dependency-failure rehearsal.
- Restart and durable-state recovery.
- Tenant/workspace isolation verification after deployment.
- Rollback/recover-forward verification.

Passing repository CI is necessary but does not replace these deployed-environment checks.
