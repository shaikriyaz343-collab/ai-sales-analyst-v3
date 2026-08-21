# Release Process

Release gates now have three layers:

1. Python/runtime contract checks.
2. Browser acceptance checks in Chromium against the deployed application.
3. Human exploratory review only for genuinely new UX/product decisions.

A green Python test suite alone is not a release approval.
