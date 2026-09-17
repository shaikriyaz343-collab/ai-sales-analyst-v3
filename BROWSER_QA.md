# Browser QA — Legacy / V4 Separation

This file documents the legacy Streamlit browser-QA history. It is not the
V4 SaaS release gate.

The legacy browser workflow uses Streamlit's documented `/_stcore/health`
endpoint and remains associated with the `main` branch. Historical notes here
should not be interpreted as evidence for the V4 Next.js/FastAPI deployment.

## V4 browser acceptance

The V4 release gate is defined in `docs/V4_DEPLOYED_QA_GATE.md` and implemented
in `.github/workflows/browser-qa.yml`.

For `v4/saas-foundation`, the workflow uses:

- `V4_APP_URL` for the deployed V4 frontend;
- `V4_E2E_API_URL` for the deployed V4 FastAPI service used by browser auth
  setup;
- `e2e/v4-playwright.config.js` for the V4 SaaS acceptance suite.

A V4 release is not browser-certified unless the dedicated V4 Playwright run
passes against the exact deployed release/build and its artifact is traceable
to that deployment identity.

Historical V4 7/7 browser acceptance evidence remains supporting historical
evidence only and does not close the current deployed-release gate by itself.
