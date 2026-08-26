from __future__ import annotations

from backend.api.services.onboarding import _capabilities, _semantic_summary


class DummyFrame:
    columns = ["OrderID", "OrderDate", "TotalAmount", "Region"]


def test_semantic_model_and_capabilities_are_separate() -> None:
    semantic = _semantic_summary(
        {},
        {"available_concepts": ["revenue", "order_id", "region"]},
        DummyFrame(),
    )
    caps = _capabilities(None, {"suggested_modules": ["Overview", "Regions"]})

    assert semantic.fields == ["OrderID", "OrderDate", "TotalAmount", "Region"]
    assert semantic.concepts == ["order_id", "region", "revenue"]
    assert semantic.metrics == ["revenue"]
    assert semantic.dimensions == ["order_id", "region"]
    assert caps["workspaces"] == ["overview", "explore", "insights", "ask", "actions", "reports"]
    assert caps["modules"] == ["Overview", "Regions"]
    assert "revenue" not in caps["modules"]
