from __future__ import annotations

from io import BytesIO

import pandas as pd

from backend.api.services.ask import answer_question
from backend.api.services.onboarding import onboard
from backend.api.services.overview import build_overview
from business_type_detector_v1 import detect_business_type
from schema_profiler_v2 import profile_dataframe
from semantic_business_model_v2 import build_semantic_model


def test_ambiguous_file_is_not_classified_into_a_business_model() -> None:
    data = pd.DataFrame({"Stage": ["Open", "Won"], "Amount": [1000, 5000], "Status": ["Active", "Closed"]})
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
    assert "revenue" not in summary.semantic.metrics


def test_derived_sales_are_explicitly_labeled() -> None:
    content = (
        b"OrderID,OrderDate,CustomerName,ProductName,Quantity,UnitPrice\n"
        b"1,2026-01-01,A,Phone,1,700\n"
        b"2,2026-01-02,B,Shirt,2,50\n"
    )
    summary = onboard("derived-retail.csv", BytesIO(content))
    assert summary.business_model == "transactional_sales"
    assert summary.analysis_status == "ready"
    overview = build_overview(summary.dataset_id)
    revenue = next(item for item in overview.metrics if item.id == "revenue")
    assert revenue.value == 800
    assert revenue.label == "Gross sales (derived)"
    assert revenue.evidence.calculation == "sum(quantity × unit price)"


def test_return_rate_uses_orders_not_rows_for_multi_line_orders() -> None:
    content = (
        b"OrderID,OrderDate,CustomerName,ProductName,Quantity,UnitPrice,TotalAmount,Return Status\n"
        b"1,2026-01-01,A,Phone,1,700,700,Returned\n"
        b"1,2026-01-01,A,Case,1,20,20,No\n"
        b"2,2026-01-02,B,Shirt,2,50,100,No\n"
    )
    summary = onboard("multi-line-retail.csv", BytesIO(content))
    overview = build_overview(summary.dataset_id)
    return_metric = next(item for item in overview.metrics if item.id == "return_rate")
    assert return_metric.value == 50.0
    assert return_metric.evidence.calculation == "returned orders / total orders × 100"


def test_unsupported_question_is_declined() -> None:
    content = (
        b"SubscriptionID,CustomerName,Plan,StartDate,MRR,ChurnStatus\n"
        b"S1,A,Pro,2026-01-01,100,Active\n"
        b"S2,B,Basic,2026-01-03,50,Churned\n"
    )
    summary = onboard("subscription.csv", BytesIO(content))
    result = answer_question(summary.dataset_id, "What is return rate?")
    assert result.answer.status == "unsupported"
    assert "won't guess" in result.answer.text
