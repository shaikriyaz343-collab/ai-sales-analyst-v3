from __future__ import annotations

from io import BytesIO

from backend.api.services.onboarding import onboard
from backend.api.services.overview import build_overview
from business_type_detector_v1 import detect_business_type
from semantic_business_model_v2 import build_semantic_model
from schema_profiler_v2 import profile_dataframe

import pandas as pd


def test_ambiguous_file_is_not_classified_into_a_business_model() -> None:
    data = pd.DataFrame(
        {
            "Stage": ["Open", "Won"],
            "Amount": [1000, 5000],
            "Status": ["Active", "Closed"],
        }
    )
    profile = profile_dataframe(data)
    semantic = build_semantic_model(profile, data=data)
    result = detect_business_type(semantic, profile)

    assert result["primary_type"] is None
    assert result["status"] == "needs_review"
    assert result["confidence"] == 0.0


def test_transactional_file_with_ambiguous_revenue_basis_is_not_analyzed() -> None:
    content = (
        b"OrderID,OrderDate,CustomerName,ProductName,Quantity,UnitPrice,Discount %\n"
        b"1,2026-01-01,A,Phone,1,700,10\n"
        b"2,2026-01-02,B,Shirt,2,50,5\n"
    )
    summary = onboard("ambiguous-retail.csv", BytesIO(content))

    assert summary.business_model is None
    assert summary.analysis_status == "needs_review"
    assert summary.semantic.metrics.count("revenue") == 0


def test_transactional_file_without_adjustments_can_use_derived_gross_value() -> None:
    content = (
        b"OrderID,OrderDate,CustomerName,ProductName,Quantity,UnitPrice\n"
        b"1,2026-01-01,A,Phone,1,700\n"
        b"2,2026-01-02,B,Shirt,2,50\n"
    )
    summary = onboard("derived-retail.csv", BytesIO(content))

    assert summary.business_model == "transactional_sales"
    assert summary.analysis_status == "ready"
    assert "revenue" in summary.semantic.metrics

    overview = build_overview(summary.dataset_id)
    revenue = next(item for item in overview.metrics if item.id == "revenue")
    assert revenue.value == 800
    assert revenue.label == "Gross sales (derived)"
    assert revenue.evidence.calculation == "sum(quantity × unit price)"


def test_return_rate_uses_orders_not_rows_when_order_has_multiple_lines() -> None:
    content = (
        b"OrderID,OrderDate,CustomerName,ProductName,Quantity,UnitPrice,TotalAmount,Return Status\n"
        b"1,2026-01-01,A,Phone,1,700,700,Returned\n"
        b"1,2026-01-01,A,Case,1,20,20,No\n"
        b"2,2026-01-02,B,Shirt,2,50,100,No\n"
    )
    summary = onboard("multi-line-retail.csv", BytesIO(content))

    assert summary.business_model == "transactional_sales"
    overview = build_overview(summary.dataset_id)
    return_metric = next(item for item in overview.metrics if item.id == "return_rate")
    assert return_metric.value == 50.0
    assert return_metric.evidence.calculation == "returned orders / total orders × 100"


def test_unsupported_question_is_explicitly_declined() -> None:
    content = (
        b"SubscriptionID,CustomerName,Plan,StartDate,MRR,ChurnStatus\n"
        b"S1,A,Pro,2026-01-01,100,Active\n"
        b"S2,B,Basic,2026-01-03,50,Churned\n"
    )
    summary = onboard("subscription.csv", BytesIO(content))
    from backend.api.services.ask import answer_question

    result = answer_question(summary.dataset_id, "What is return rate?")
    assert result.answer.status == "unsupported"
    assert "won't guess" in result.answer.text
