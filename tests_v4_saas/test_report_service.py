from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest

from backend.api.services.onboarding import onboard
from backend.api.services.report import build_report
from fastapi.testclient import TestClient
from backend.api.services.session import create_session, update_scope
from backend.api.services import overview

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def _load(name: str):
    with (SAMPLES / name).open("rb") as fh:
        return onboard(name, fh)


@pytest.mark.parametrize(
    "name,model",
    [
        ("retail.csv","transactional_sales"),
        ("pipeline.csv","sales_pipeline"),
        ("subscription.csv","subscription"),
        ("services.csv","services"),
    ],
)
def test_report_reuses_validated_business_model(name, model):
    summary = _load(name)
    response = build_report(summary.dataset_id)
    assert response.business_model == model
    assert response.file_name == name
    assert response.metrics
    assert response.title.startswith("Executive report")
    assert response.source_note


def test_report_preserves_scope_and_evidence(monkeypatch, tmp_path):
    monkeypatch.setattr(overview, "STORAGE", tmp_path)
    import backend.api.services.onboarding as onboarding
    import backend.api.services.session as session_service
    monkeypatch.setattr(onboarding, "STORAGE", tmp_path)
    monkeypatch.setattr(overview, "STORAGE", tmp_path)
    monkeypatch.setattr(session_service, "STORAGE", tmp_path)
    monkeypatch.setattr(session_service, "SESSION_STORAGE", tmp_path / "sessions")
    summary = _load("retail.csv")
    session = create_session(summary.dataset_id)
    from backend.api.contracts import ScopeFilter
    session = update_scope(session.session_id, [ScopeFilter(field="region", operator="in", values=["North"])])
    response = build_report(summary.dataset_id, scope=session.scope)
    assert response.scope_label == "region = North"
    assert all(metric.evidence.scope == "region = North" for metric in response.metrics)
    assert all(item.evidence.scope == "region = North" for item in response.attention + response.opportunities)
    assert all(action.evidence.scope == "region = North" for action in response.actions)


def test_report_missing_dataset_rejected():
    with pytest.raises(ValueError, match="Dataset not found"):
        build_report("does-not-exist")


def test_report_api_endpoint_returns_composed_report():
    client = TestClient(__import__("backend.api.main", fromlist=["app"]).app)
    signup = client.post("/api/v1/auth/signup", json={"email": f"report-{uuid4().hex}@example.com", "password": "StrongPassword1!", "name": "Report User", "organization_name": "Report Org"})
    assert signup.status_code == 200
    sample = SAMPLES / "pipeline.csv"
    with sample.open("rb") as fh:
        uploaded = client.post("/api/v1/onboarding/profile", files={"file": ("pipeline.csv", fh, "text/csv")})
    assert uploaded.status_code == 200, uploaded.text
    summary = uploaded.json()["dataset"]
    response = client.get(f"/api/v1/datasets/{summary['dataset_id']}/report", params={"session_id": uploaded.json()["session_id"]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dataset_id"] == summary["dataset_id"]
    assert body["business_model"] == "sales_pipeline"
    assert body["metrics"]
    assert body["actions"] or body["attention"] or body["opportunities"]
