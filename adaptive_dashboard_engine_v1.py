
from __future__ import annotations

from typing import Any


MODULE_DEFINITIONS = {
    "overview": {
        "title": "Overview",
        "icon": "🏠",
        "description": "A quick view of overall business performance.",
        "priority": 1,
    },
    "attention": {
        "title": "What Needs Your Attention",
        "icon": "🚦",
        "description": "Important changes, risks, and unusual movements.",
        "priority": 2,
    },
    "performance": {
        "title": "Performance",
        "icon": "📈",
        "description": "Revenue, orders, volume, and trends.",
        "priority": 3,
    },
    "products": {
        "title": "Products",
        "icon": "📦",
        "description": "Product and SKU performance.",
        "priority": 4,
    },
    "customers": {
        "title": "Customers",
        "icon": "👥",
        "description": "Customer contribution and concentration.",
        "priority": 5,
    },
    "regions": {
        "title": "Regions",
        "icon": "🌎",
        "description": "Regional performance.",
        "priority": 6,
    },
    "sales_team": {
        "title": "Sales Team",
        "icon": "🎯",
        "description": "Salesperson and team performance.",
        "priority": 7,
    },
    "discounts": {
        "title": "Discounts",
        "icon": "🏷️",
        "description": "Discount levels and their business impact.",
        "priority": 8,
    },
    "returns": {
        "title": "Returns",
        "icon": "↩️",
        "description": "Return activity and returned value.",
        "priority": 9,
    },
    "channels": {
        "title": "Channels",
        "icon": "🛒",
        "description": "Performance by sales channel.",
        "priority": 10,
    },
    "payments": {
        "title": "Payments",
        "icon": "💳",
        "description": "Payment-method mix.",
        "priority": 11,
    },
    "order_status": {
        "title": "Order Status",
        "icon": "📋",
        "description": "Delivered, shipped, cancelled, and other statuses.",
        "priority": 12,
    },
    "profitability": {
        "title": "Costs & Margin",
        "icon": "💰",
        "description": "Cost, margin, and profitability analysis.",
        "priority": 13,
    },
    "pipeline": {
        "title": "Pipeline",
        "icon": "📊",
        "description": "Pipeline value, stages, and conversion.",
        "priority": 14,
    },
    "forecast": {
        "title": "Sales Forecast",
        "icon": "🔮",
        "description": "Forecast and expected sales.",
        "priority": 15,
    },
    "recurring_revenue": {
        "title": "Recurring Revenue",
        "icon": "🔁",
        "description": "MRR, ARR, and recurring-revenue movement.",
        "priority": 16,
    },
    "retention": {
        "title": "Retention",
        "icon": "🧲",
        "description": "Retention and customer continuity.",
        "priority": 17,
    },
    "churn": {
        "title": "Churn",
        "icon": "📉",
        "description": "Churn and cancellation analysis.",
        "priority": 18,
    },
    "services": {
        "title": "Services",
        "icon": "🧰",
        "description": "Service delivery and revenue.",
        "priority": 19,
    },
    "billings": {
        "title": "Billings",
        "icon": "🧾",
        "description": "Billings and client contribution.",
        "priority": 20,
    },
    "utilization": {
        "title": "Utilization",
        "icon": "⏱️",
        "description": "Hours and utilization patterns.",
        "priority": 21,
    },
    "ask": {
        "title": "Ask Your Business Analyst",
        "icon": "💬",
        "description": "Ask questions in plain English.",
        "priority": 90,
    },
    "report": {
        "title": "Executive Report",
        "icon": "📄",
        "description": "A shareable business summary.",
        "priority": 91,
    },
    "data_quality": {
        "title": "Data Quality",
        "icon": "✅",
        "description": "Checks that affect analysis reliability.",
        "priority": 92,
    },
}


def _has(model: dict[str, Any], concept: str) -> bool:
    return concept in set(
        model.get(
            "available_concepts",
            [],
        )
    )


def build_dashboard_plan(
    semantic_model: dict[str, Any],
    business_type: dict[str, Any],
    adaptive_analysis: dict[str, Any],
    data_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:

    capabilities = semantic_model.get(
        "capabilities",
        {}
    )

    primary_type = business_type.get(
        "primary_type"
    )

    sections: list[str] = [
        "overview",
        "attention",
        "performance",
    ]

    # Transactional analysis.
    if capabilities.get(
        "product_analysis"
    ):
        sections.append(
            "products"
        )

    if capabilities.get(
        "customer_analysis"
    ):
        sections.append(
            "customers"
        )

    if capabilities.get(
        "regional_analysis"
    ):
        sections.append(
            "regions"
        )

    if capabilities.get(
        "sales_team_analysis"
    ):
        sections.append(
            "sales_team"
        )

    if capabilities.get(
        "discount_analysis"
    ):
        sections.append(
            "discounts"
        )

    if capabilities.get(
        "return_analysis"
    ):
        sections.append(
            "returns"
        )

    if capabilities.get(
        "channel_analysis"
    ):
        sections.append(
            "channels"
        )

    if capabilities.get(
        "payment_analysis"
    ):
        sections.append(
            "payments"
        )

    if capabilities.get(
        "order_status_analysis"
    ):
        sections.append(
            "order_status"
        )

    if capabilities.get(
        "profitability_analysis"
    ):
        sections.append(
            "profitability"
        )

    # Business-type-specific sections.
    if primary_type == "sales_pipeline":
        sections.append("pipeline")

        # Forecast is only shown when the dataset contains enough
        # information to calculate an expected-close forecast.
        has_close_date = (
            _has(semantic_model, "expected_close")
            or _has(semantic_model, "close_date")
        )
        has_amount = (
            _has(semantic_model, "amount")
            or _has(semantic_model, "pipeline_amount")
            or _has(semantic_model, "revenue")
        )

        if has_close_date and has_amount:
            sections.append("forecast")

    elif primary_type == "subscription":
        sections.extend(
            [
                "recurring_revenue",
                "retention",
                "churn",
            ]
        )

    elif primary_type == "services":
        sections.extend(
            [
                "services",
                "billings",
                "utilization",
            ]
        )

    # Always provide these two end-user actions.
    sections.extend(
        [
            "ask",
            "report",
        ]
    )

    # Data quality is part of the trust contract, so it is always visible.
    sections.append("data_quality")

    # Deduplicate while preserving order.
    sections = list(
        dict.fromkeys(
            sections
        )
    )

    # Convert section IDs to UI metadata.
    section_specs = []

    for section in sections:
        spec = MODULE_DEFINITIONS.get(
            section
        )

        if spec:
            section_specs.append(
                {
                    "id": section,
                    **spec,
                }
            )

    # Recommended first screen.
    primary_cta = (
        "Review your business"
        if primary_type
        else "Start with your business overview"
    )

    # Recommended onboarding message.
    if primary_type == "transactional_sales":
        onboarding = (
            "We found transactional sales data. "
            "We'll focus first on revenue, orders, products, customers, and the "
            "additional fields your file contains."
        )
    elif primary_type == "sales_pipeline":
        onboarding = (
            "We found sales-pipeline data. "
            "We'll focus on pipeline value, stages, win/loss performance, and "
            "sales-team performance."
        )
    elif primary_type == "subscription":
        onboarding = (
            "We found recurring-revenue data. "
            "We'll focus on MRR, retention, renewals, and churn."
        )
    elif primary_type == "services":
        onboarding = (
            "We found services data. "
            "We'll focus on billings, hours, clients, and utilization."
        )
    else:
        onboarding = (
            "We've reviewed your file and will show the analysis your data supports."
        )

    return {
        "business_type": business_type,
        "sections": section_specs,
        "section_ids": sections,
        "primary_cta": primary_cta,
        "onboarding_message": onboarding,
        "analysis_module_count": adaptive_analysis.get(
            "module_count",
            0,
        ),
        "data_quality": data_quality,
    }


def get_visible_sections(
    plan: dict[str, Any]
) -> list[dict[str, Any]]:
    return plan.get(
        "sections",
        []
    )


def get_navigation_labels(
    plan: dict[str, Any]
) -> list[str]:
    return [
        f"{section['icon']} {section['title']}"
        for section in plan.get(
            "sections",
            []
        )
    ]
