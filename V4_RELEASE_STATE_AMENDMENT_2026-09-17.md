# AI Sales Analyst V4 — Release-State Amendment

Date: 2026-09-17
Branch: `v4/saas-foundation`

## Current release identity

Current repository head:

`ff67e2e495407646732079ff6a90a55438ed8fb1`

Latest application-behavior checkpoint remains:

`371aa5caf00308b98faeba58bf4c5736bb995b39`

The commits after that application checkpoint are release-QA / evidence / test-hardening changes; the latest application behavior remains anchored at `371aa5caf...` except for the deployed tenant-isolation browser-test fix recorded in `ff67e2e...`.

## Current production targets

V4 frontend:

`https://peaceful-mindfulness-production-51b6.up.railway.app`

V4 FastAPI:

`https://ai-sales-analyst-v3-production.up.railway.app`

The deployed API was directly reachable from the GitHub Actions runner at `/api/v1/health` and returned:

`{"status":"ok","product":"AI Sales Analyst","version":"4.1.0-alpha.1"}`

## Current CI / deployed browser acceptance

The exact deployed V4 Playwright suite ran against the public V4 frontend/API targets on commit `ff67e2e495407646732079ff6a90a55438ed8fb1`.

Workflow run:

`35190811161`

Browser job:

`105102746309`

The job completed successfully. All 8 V4 acceptance tests passed:

1. onboarding creates a dataset-backed workspace
2. scope persists across workspaces
3. dataset replacement creates a clean analytical session
4. executive report uses the current session and survives replacement
5. monitoring creates and evaluates a session-scoped alert
6. saved intelligence persists across refresh and can reopen an analysis
7. deployed tenant isolation rejects cross-organization dataset access
8. authentication lifecycle supports sign-up, sign-out, and sign-in

Result: **8 passed**.

The tenant-isolation test used two independent API contexts against the deployed FastAPI service and verified that the second organization received `404` for both the first organization's dataset and overview access.

Browser artifact:

`v4-browser-qa-results` — artifact ID `10483038543`

Artifact SHA-256:

`6790bac31d6dc07e934e50793deaec951fdf56405685e10ac6f9583517acd1b4`

Artifact URL:

`https://github.com/shaikriyaz343-collab/ai-sales-analyst-v3/actions/runs/35190811161/artifacts/10483038543`

## Railway deployment identity

Both Railway deployment statuses for commit `ff67e2e495407646732079ff6a90a55438ed8fb1` are `success`:

- Frontend service `731a2cff-42db-4bc0-bc21-073d64ebfc34`; deployment `ba611fa3-4c30-4467-9a3a-70f1312a1028`; hostname `peaceful-mindfulness-production-51b6.up.railway.app`.
- API service `c1446578-b14e-4ef9-b3cb-bbf3156ccb1d`; deployment `5e9c2dbf-f789-4934-8594-56433c420b3a`; hostname `ai-sales-analyst-v3-production.up.railway.app`.

The browser job checked out commit `ff67e2e...`, successfully reached both deployed services, and then completed the full V4 suite.

## R2 production visual evidence

A current Cloudflare dashboard capture records:

- bucket `ai-sales-analyst-v4-prod`;
- prefix `v4/`;
- four visible CSV objects;
- Public Access `Disabled`;
- Standard storage class;
- non-zero stored data and operation counts.

The capture is preserved in `V4_R2_VISUAL_EVIDENCE_2026-09-17.md` as supporting visual evidence.

It supports production bucket existence, private posture, and persisted CSV presence. It does **not** by itself prove provider-failure injection, HTTP 503 behavior during outage, or recovery after restoration.

## Gate status

### Closed with exact deployed evidence

- Exact-release V4 browser acceptance: **CLOSED** — 8/8 passed on the deployed V4 frontend/API with Railway deployment identities tied to the same commit.
- Deployed tenant-isolation browser verification: **CLOSED** — the deployed acceptance suite passed the cross-organization denial scenario.
- Repository-side post-promotion security review: **CLOSED**.
- Repository-side object-store provider-failure HTTP 503 contract: **CLOSED**.

### Still open

- Controlled production R2/provider failure → HTTP 503 → recovery evidence.
- Linux/container resource/capacity measurements.
- Deployed restart/durable-state recovery evidence tied to the release.
- Release-linked rollback/recover-forward evidence.
- Measured production monitoring/alert evidence and ownership.
- Final cross-site frontend/API topology decision and verification under issue #13.
- Complete production cutover/release evidence package.

Owner/operator statements remain search leads only and do not close any of these gates without directly reviewable evidence.

## Browser workflow hardening

The normal V4 browser workflow uses the recorded production frontend/API targets as fallbacks when repository variables are absent, while still allowing `V4_APP_URL` and `V4_E2E_API_URL` to override them. The dedicated explicit-target workflow is dispatch-only.

The V4 health contract is `/api/v1/health`; `/api/v1/ready` remains the readiness endpoint. Legacy Streamlit browser QA remains isolated to `main` and is not a V4 release gate.

This amendment supersedes older state snapshots that still list earlier branch heads or the pre-certification browser state.
