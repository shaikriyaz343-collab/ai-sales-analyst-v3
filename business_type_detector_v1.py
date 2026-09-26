from __future__ import annotations

from typing import Any


LABELS = {
    "transactional_sales": "Transactional / Retail Sales",
    "sales_pipeline": "Sales Pipeline",
    "subscription": "Subscription / Recurring Revenue",
    "services": "Services / Professional Services",
}

REQUIRED_EVIDENCE = {
    "transactional_sales": (
        {"date", "customer", "product", "quantity", "revenue"},
    ),
    "sales_pipeline": (
        {"stage"},
        ({"amount"}, {"revenue"}),
        ({"opportunity_id"}, {"customer"}),
        ({"probability"}, {"expected_close"}),
    ),
    "subscription": (
        ({"mrr"},),
        ({"subscription_id"}, {"customer"}),
        ({"churn_status"}, {"renewal_status"}, {"plan"}),
    ),
    "services": (
        {"hours"},
        {"billings"},
        ({"project_id"}, {"client"}),
    ),
}


def _has_required(available: set[str], requirement: Any) -> bool:
    if isinstance(requirement, set):
        return requirement.issubset(available)
    return any(option.issubset(available) for option in requirement)


def _model_supported(model: str, available: set[str]) -> bool:
    return all(_has_required(available, item) for item in REQUIRED_EVIDENCE[model])


def _modules(primary: str | None, available: set[str]) -> list[str]:
    if not primary:
        return []

    modules = [
        "Overview",
        "What Needs Attention",
        "Performance",
        "Ask Your Business Analyst",
        "Executive Report",
    ]

    conditional = {
        "product": "Products",
        "customer": "Customers",
        "region": "Regions",
        "salesperson": "Sales Team",
        "discount_pct": "Discounts",
        "discount_amount": "Discounts",
        "return_status": "Returns",
        "return_amount": "Returns",
        "channel": "Channels",
        "payment_method": "Payments",
        "order_status": "Order Status",
        "sku": "SKUs",
        "cost": "Costs & Margin",
    }
    for concept, module in conditional.items():
        if concept in available and module not in modules:
            modules.append(module)

    if primary == "sales_pipeline":
        modules += ["Pipeline", "Stage Performance", "Sales Forecast"]
    elif primary == "subscription":
        modules += ["Recurring Revenue", "Retention", "Churn"]
    elif primary == "services":
        modules += ["Services", "Billings", "Utilization"]

    return modules


def detect_business_type(semantic_model: dict, profile: dict) -> dict:
    """Conservative classifier: unsupported or ambiguous datasets are review-only."""
    available = set(semantic_model.get("available_concepts", []))
    names = " ".join(
        str(x.get("original_name", "")).lower()
        for x in profile.get("fields", [])
    )

    scores = {
        "transactional_sales": 2 * sum(
            x in available for x in ["product", "quantity", "revenue", "order_id"]
        ) + sum(x in available for x in ["discount_pct", "return_status"]),
        "sales_pipeline": sum(
            term in names
            for term in ["opportunity", "stage", "probability", "salesperson", "expected close", "forecast"]
        ),
        "subscription": sum(
            term in names
            for term in ["subscription", "mrr", "arr", "churn", "renewal", "recurring", "plan"]
        ),
        "services": sum(
            term in names
            for term in ["project", "hours", "billable", "hourly rate", "consultant", "employee"]
        ),
    }

    supported = [model for model in scores if _model_supported(model, available)]

    if not supported:
        return {
            "primary_type": None,
            "primary_label": "Data model needs review",
            "confidence": 0.0,
            "scores": scores,
            "suggested_modules": [],
            "status": "needs_review",
            "reason": "The uploaded file does not contain enough validated fields to identify one supported business model safely.",
        }

    ranked = sorted(supported, key=lambda model: (-scores[model], model))
    primary = ranked[0]

    if len(ranked) > 1 and scores[ranked[0]] - scores[ranked[1]] < 2:
        return {
            "primary_type": None,
            "primary_label": "Data model needs review",
            "confidence": 0.0,
            "scores": scores,
            "suggested_modules": [],
            "status": "needs_review",
            "reason": "More than one supported business model matches the uploaded fields too closely to classify safely.",
        }

    total = sum(scores[m] for m in supported)
    confidence = scores[primary] / total if total else 0.0

    return {
        "primary_type": primary,
        "primary_label": LABELS[primary],
        "confidence": round(min(confidence, 1.0), 2),
        "scores": scores,
        "suggested_modules": _modules(primary, available),
        "status": "ready",
        "reason": "",
    }
