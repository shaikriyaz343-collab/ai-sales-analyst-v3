# Browser Acceptance QA

The previous runtime checks are useful for code contracts, but they do not prove
the user experience. This suite runs a real Chromium browser against the deployed
Streamlit application.

## What it checks

For all four representative business archetypes:

- Upload the real sample file.
- Start analysis.
- Verify detected business type and full-file metrics.
- Navigate through the Review Your Business sections.
- Detect visible exceptions such as Traceback/ImportError/KeyError/StreamlitAPIException.
- Apply a business-specific scope.
- Verify the scope is reflected in the UI.
- Reject misleading scoped concentration wording.
- Ask a factual question and verify the expected entity/metric appears.
- Change the question and verify the old answer is not presented as current.
- Clear the question and verify the answer disappears.

## Run against the deployed app

Set a GitHub repository variable:

`APP_URL = https://YOUR-APP.streamlit.app`

The workflow runs automatically after pushes to `main` and can also be run manually.

This is intentionally separate from the Python unit/runtime diagnostics.
