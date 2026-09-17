# V4 Release State Note — 2026-09-17

## Exact deployed browser targets

The current V4 browser acceptance attempt uses the following user-supplied public deployment origins:

- Frontend: `https://peaceful-mindfulness-production-51b6.up.railway.app`
- FastAPI: `https://ai-sales-analyst-v3-production.up.railway.app`

The dedicated workflow run is `35188320422` on commit `2eea1da27729fd1021a1b25a4d829fc61ebba7b4`.

The browser job accepted both URLs and is performing the deployed-service readiness probe before Playwright. It checks the API `/health`, API `/ready`, and frontend `/` for HTTP 200 responses.

Railway reports successful deployment processing for both services on this commit:

- frontend service `731a2cff-42db-4bc0-bc21-073d64ebfc34`, deployment `41649dab-551b-4745-9a1b-157407864fe6`
- API service `c1446578-b14e-4ef9-b3cb-bbf3156ccb1d`, deployment `1d2a2671-2151-488f-9b02-ebf24610c4fa`

These deployment statuses plus the user-supplied URLs establish the target identities being exercised. They do not constitute browser acceptance until the readiness probe and Playwright suite complete successfully.
