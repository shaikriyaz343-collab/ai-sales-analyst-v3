# Browser Acceptance QA v2

The health check now uses Streamlit's documented `/_stcore/health` endpoint.
It no longer downloads the root page or follows redirects, which caused the
previous `curl: (47) Maximum (50) redirects followed` failure.

GitHub Actions are pinned to current Node 24-capable action versions.
Browser failures now reach the Playwright stage instead of being masked by
the deployment health check.
