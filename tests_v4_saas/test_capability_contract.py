from __future__ import annotations

from backend.api.services.onboarding import _capabilities


def test_capabilities_are_separated_for_retail() -> None:
    caps = _capabilities(
        {"available_concepts": ["revenue", "return_status", "product", "customer"]},
        {"suggested_modules": ["Overview", "Products", "Returns", "What Needs Attention"]},
    )

    assert caps["workspaces"] == ["overview", "explore", "insights", "ask", "actions", "reports"]
    assert caps["modules"] == ["Overview", "Products", "Returns", "What Needs Attention"]
    assert "revenue" not in caps["modules"]


def test_capabilities_are_separated_for_pipeline() -> None:
    caps = _capabilities(
        {"available_concepts": ["amount", "stage", "salesperson", "probability"]},
        {"suggested_modules": ["Pipeline", "Sales Forecast", "Stage Performance"]},
    )

    assert caps["workspaces"] == ["overview", "explore", "insights", "ask", "actions", "reports"]
    assert caps["modules"] == ["Pipeline", "Sales Forecast", "Stage Performance"]
    assert "Products" not in caps["modules"]
