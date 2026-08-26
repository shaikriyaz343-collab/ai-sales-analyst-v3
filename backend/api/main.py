from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .contracts import HealthResponse, OnboardingResponse, OverviewResponse
from .services.onboarding import get_dataset, onboard
from .services.overview import build_overview

app = FastAPI(title="AI Sales Analyst API", version="4.0.0-alpha.1", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])

@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", product="AI Sales Analyst", version="4.0.0-alpha.1")

@app.post("/api/v1/onboarding/profile", response_model=OnboardingResponse)
async def profile_upload(file: UploadFile = File(...)) -> OnboardingResponse:
    try:
        summary = onboard(file.filename or "upload", file.file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not understand this file: {exc}") from exc
    return OnboardingResponse(dataset=summary, message="Your dataset is ready for analysis.")

@app.get("/api/v1/datasets/{dataset_id}")
def dataset(dataset_id: str):
    summary = get_dataset(dataset_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return summary

@app.get("/api/v1/datasets/{dataset_id}/overview", response_model=OverviewResponse)
def overview(dataset_id: str) -> OverviewResponse:
    try:
        return build_overview(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not build overview: {exc}") from exc
