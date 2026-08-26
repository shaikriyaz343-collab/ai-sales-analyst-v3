# AI Sales Analyst V4 — SaaS Foundation Setup

This phase starts the new SaaS frontend/backend architecture. It does not replace or delete the frozen V3 app.

## Recommended branch
Keep the previous Streamlit experiment separate. Create a fresh branch from the frozen V3 commit before adding these files:

```powershell
git switch main
git pull origin main
git switch -c v4/saas-foundation
```

The target baseline is `b8b7ad5`.

## Backend

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.api.main:app --reload --port 8000
```

API:

- `GET http://localhost:8000/api/v1/health`
- `POST http://localhost:8000/api/v1/onboarding/profile`
- `GET http://localhost:8000/api/v1/datasets/{dataset_id}`

The onboarding API reuses the V3 profiler, semantic model, business-model detector, and data-quality engine. Numeric sales metrics are deliberately not generated yet.

## Frontend

Next.js 16.x currently requires Node.js 20.9 or newer. Verify:

```powershell
node --version
```

Then:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

If your machine cannot reach npm, do not substitute random package versions. Use the versions in `frontend/package.json` once package installation is available.

## Phase 1 browser acceptance

1. Open the V4 web app.
2. Upload CSV/XLSX/XLS.
3. Confirm file name, row count, field count and detected business model.
4. Navigate Overview -> Explore -> Insights -> Ask Analyst -> Actions -> Reports.
5. Confirm navigation changes URL/workspace but does not mutate dataset state.
6. Upload a different dataset and confirm the previous dataset metadata is replaced.
7. Refresh and confirm the dataset session can be rehydrated from the backend metadata store while the backend is running.
8. Try an unsupported file and confirm a controlled error.

## Important

The current backend stores development uploads and metadata under `backend/runtime_data/`. This is intentionally a development-only storage adapter. It must be replaced by object storage + database persistence before production SaaS launch.
