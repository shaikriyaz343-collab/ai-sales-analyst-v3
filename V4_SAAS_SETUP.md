# AI Sales Analyst V4 — SaaS Setup & Release Gates

## Branch and baseline
Target branch: `v4/saas-foundation`
Frozen V3 baseline: `b8b7ad5`

The previous Streamlit V4 experiment remains historical/reference only. New product work belongs in the SaaS frontend + FastAPI backend.

## Backend
From the repository root, using the dedicated V4 environment:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api.main:app --reload --port 8000
```

API:
- `GET /api/v1/health`
- `POST /api/v1/onboarding/profile`
- `GET /api/v1/datasets/{dataset_id}`
- `GET /api/v1/datasets/{dataset_id}/overview`
- `GET /api/v1/datasets/{dataset_id}/explore`
- `GET /api/v1/datasets/{dataset_id}/insights`

The onboarding endpoint reuses the existing V3 profiler, semantic model, business-model detector, and data-quality engine.

## Frontend
Node.js 20.9+ is required by the Next.js 16.x project.

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Integrated test gates
Backend:
```powershell
python -m pytest -q tests_v4_saas
```

Frontend:
```powershell
cd frontend
npm run build
```

Do not consider a UI feature complete until the frontend build passes and the browser flow is validated.

## Current browser-validated flows
- SaaS onboarding with Retail/Pipeline dataset replacement.
- Executive Overview for Retail/Pipeline/Subscription/Services.
- Explore metric/dimension consistency.
- Explore dataset replacement resets to a valid business-model-specific query.

## Development storage
`backend/runtime_data/` is development-only local storage and is ignored by Git. Before production SaaS launch, replace it with object storage + database persistence.

## Product trust rules
- Deterministic calculations own numeric truth.
- AI explains validated results only.
- Every material insight carries evidence and scope.
- Unsupported analyses are declined instead of guessed.
- UI state does not become analytical state.
