# V4 SaaS Integrated Release Gate

Run from the repository root on `v4/saas-foundation`.

## Backend
```powershell
python -m pytest -q tests_v4_saas
```

Expected at the current milestone: 20 passing.

## Frontend
```powershell
cd frontend
npm.cmd run build
```

## Browser
With FastAPI on `http://localhost:8000` and Next.js on `http://localhost:3000`:
- Upload Retail.
- Confirm Overview.
- Test Explore metric/dimension consistency.
- Replace with Pipeline and confirm the Explore state becomes Pipeline-valid.
- Validate Insights before committing the Insights milestone.

## Git hygiene
Do not stage:
- `.venv-v4/`
- `frontend/node_modules/`
- `frontend/.next/`
- `backend/runtime_data/`

## Source-of-truth rule
Do not hand-edit numeric outputs in the frontend. Metrics, comparisons, insights, and evidence originate in the backend analytical layer.
