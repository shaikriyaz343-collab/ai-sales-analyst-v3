from io import BytesIO
from pathlib import Path

import pandas as pd

from backend.api.services.onboarding import onboard


def test_onboard_reuses_v3_semantic_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.api.services.onboarding.STORAGE", tmp_path)
    content = b"date,product,customer,quantity,price,revenue,return_status\n2026-01-01,Phone,A,2,100,200,No\n2026-01-02,Laptop,B,1,500,500,Yes\n"
    summary = onboard("sample.csv", BytesIO(content))
    assert summary.row_count == 2
    assert summary.column_count == 7
    assert summary.business_model == "transactional_sales"
    assert "revenue" in summary.semantic.concepts
    assert "revenue" in summary.supported_concepts
    assert "return_status" in summary.supported_concepts


def test_onboard_rejects_unsupported_extension(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.api.services.onboarding.STORAGE", tmp_path)
    try:
        onboard("sample.txt", BytesIO(b"hello"))
    except ValueError as exc:
        assert "Supported files" in str(exc)
    else:
        raise AssertionError("Unsupported file type should be rejected")
