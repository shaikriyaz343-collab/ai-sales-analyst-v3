
from __future__ import annotations

def detect_business_type(semantic_model: dict, profile: dict) -> dict:
    available = set(semantic_model.get("available_concepts", []))
    names = " ".join(
        x["original_name"].lower()
        for x in profile.get("fields", [])
    )

    scores = {
        "transactional_sales": 0,
        "sales_pipeline": 0,
        "subscription": 0,
        "services": 0,
    }

    scores["transactional_sales"] += 2 * sum(
        x in available for x in ["product","quantity","revenue","order_id"]
    )
    scores["transactional_sales"] += sum(
        x in available for x in ["discount_pct","return_status"]
    )

    scores["sales_pipeline"] += sum(
        term in names for term in [
            "opportunity","stage","probability",
            "salesperson","expected close","forecast"
        ]
    )

    scores["subscription"] += sum(
        term in names for term in [
            "subscription","mrr","arr","churn",
            "renewal","recurring","plan"
        ]
    )

    scores["services"] += sum(
        term in names for term in [
            "project","hours","billable",
            "hourly rate","consultant","employee"
        ]
    )

    labels = {
        "transactional_sales": "Transactional / Retail Sales",
        "sales_pipeline": "Sales Pipeline",
        "subscription": "Subscription / Recurring Revenue",
        "services": "Services / Professional Services",
    }

    primary = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[primary] / total if total else 0

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

    return {
        "primary_type": primary,
        "primary_label": labels[primary],
        "confidence": round(min(confidence, 1.0), 2),
        "scores": scores,
        "suggested_modules": modules,
    }
