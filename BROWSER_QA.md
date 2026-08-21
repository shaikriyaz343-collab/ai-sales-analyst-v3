# Browser Acceptance QA — Fixed

The first browser-QA workflow had two weaknesses:
- it relied on a fixed 90-second wait instead of verifying the deployed app was actually healthy;
- it did not fail with a clear message when APP_URL was missing.

This revision adds:
- explicit APP_URL validation;
- active Streamlit health polling for up to 10 minutes;
- Node 24;
- Playwright test discovery before execution;
- reliable artifact collection;
- less fragile Streamlit selectors.

The test suite is still a real Chromium browser suite and is separate from Python runtime checks.
