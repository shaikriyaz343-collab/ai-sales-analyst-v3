
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd


CORE_CONCEPTS = {
    "date": {
        "label": "Date",
        "kind": "dimension",
        "required": True,
    },
    "order_id": {
        "label": "Order / Transaction",
        "kind": "dimension",
        "required": True,
    },
    "customer": {
        "label": "Customer",
        "kind": "dimension",
        "required": True,
    },
    "product": {
        "label": "Product",
        "kind": "dimension",
        "required": True,
    },
    "quantity": {
        "label": "Units Sold",
        "kind": "metric",
        "required": True,
    },
    "revenue": {
        "label": "Revenue",
        "kind": "metric",
        "required": False,
    },
    "price": {
        "label": "Unit Price",
        "kind": "metric",
        "required": False,
    },
}


OPTIONAL_CONCEPTS = {
    "category": {
        "label": "Product Category",
        "kind": "dimension",
    },
    "sku": {
        "label": "SKU",
        "kind": "dimension",
    },
    "discount_pct": {
        "label": "Discount %",
        "kind": "metric",
    },
    "discount_amount": {
        "label": "Discount Amount",
        "kind": "metric",
    },
    "return_status": {
        "label": "Return Status",
        "kind": "dimension",
    },
    "return_amount": {
        "label": "Return Amount",
        "kind": "metric",
    },
    "region": {
        "label": "Region",
        "kind": "dimension",
    },
    "salesperson": {
        "label": "Salesperson",
        "kind": "dimension",
    },
    "channel": {
        "label": "Sales Channel",
        "kind": "dimension",
    },
    "payment_method": {
        "label": "Payment Method",
        "kind": "dimension",
    },
    "order_status": {
        "label": "Order Status",
        "kind": "dimension",
    },
    "tax_amount": {
        "label": "Tax",
        "kind": "metric",
    },
    "shipping_amount": {
        "label": "Shipping",
        "kind": "metric",
    },
    "cost": {
        "label": "Cost",
        "kind": "metric",
    },
    "currency": {
        "label": "Currency",
        "kind": "dimension",
    },
    "opportunity_id": {
        "label": "Opportunity",
        "kind": "dimension",
    },
    "stage": {
        "label": "Pipeline Stage",
        "kind": "dimension",
    },
    "amount": {
        "label": "Pipeline Amount",
        "kind": "metric",
    },
    "probability": {
        "label": "Probability",
        "kind": "metric",
    },
    "expected_close": {
        "label": "Expected Close",
        "kind": "dimension",
    },
    "subscription_id": {
        "label": "Subscription",
        "kind": "dimension",
    },
    "plan": {
        "label": "Plan",
        "kind": "dimension",
    },
    "mrr": {
        "label": "Monthly Recurring Revenue",
        "kind": "metric",
    },
    "arr": {
        "label": "Annual Recurring Revenue",
        "kind": "metric",
    },
    "churn_status": {
        "label": "Churn Status",
        "kind": "dimension",
    },
    "renewal_status": {
        "label": "Renewal Status",
        "kind": "dimension",
    },
    "project_id": {
        "label": "Project",
        "kind": "dimension",
    },
    "client": {
        "label": "Client",
        "kind": "dimension",
    },
    "service": {
        "label": "Service",
        "kind": "dimension",
    },
    "hours": {
        "label": "Hours",
        "kind": "metric",
    },
    "billings": {
        "label": "Billings",
        "kind": "metric",
    },
    "hourly_rate": {
        "label": "Hourly Rate",
        "kind": "metric",
    },
    "employee": {
        "label": "Employee",
        "kind": "dimension",
    },
}


@dataclass
class BusinessConcept:
    name: str
    label: str
    kind: str
    source_columns: list[str]
    available: bool
    derived: bool = False


def _present_fields(profile: dict[str, Any]) -> dict[str, list[str]]:
    present: dict[str, list[str]] = {}

    for semantic_name, columns in profile.get(
        "recognized",
        {}
    ).items():

        present[
            semantic_name
        ] = list(
            columns
        )

    return present


def _derive_revenue_available(
    data: pd.DataFrame,
    present: dict[str, list[str]],
) -> bool:
    if "revenue" in present:
        return True

    return (
        "quantity" in present
        and "price" in present
    )


def _derive_aov_available(
    present: dict[str, list[str]],
) -> bool:
    return (
        "revenue" in present
        and "order_id" in present
    ) or (
        "quantity" in present
        and "price" in present
        and "order_id" in present
    )


def build_semantic_model(
    profile: dict[str, Any],
    data: pd.DataFrame | None = None,
) -> dict[str, Any]:

    present = _present_fields(
        profile
    )

    concepts: list[BusinessConcept] = []

    # Core concepts.
    for name, meta in CORE_CONCEPTS.items():

        if name == "revenue":

            available = _derive_revenue_available(
                data
                if data is not None
                else pd.DataFrame(),
                present,
            )

            derived = (
                "revenue" not in present
                and available
            )

        elif name == "price":

            available = (
                "price" in present
                or (
                    "revenue" in present
                    and "quantity" in present
                )
            )

            derived = (
                "price" not in present
                and available
            )

        else:

            available = (
                name in present
            )

            derived = False

        concepts.append(
            BusinessConcept(
                name=name,
                label=meta["label"],
                kind=meta["kind"],
                source_columns=present.get(
                    name,
                    [],
                ),
                available=available,
                derived=derived,
            )
        )

    # Optional concepts.
    for name, meta in OPTIONAL_CONCEPTS.items():

        concepts.append(
            BusinessConcept(
                name=name,
                label=meta["label"],
                kind=meta["kind"],
                source_columns=present.get(
                    name,
                    [],
                ),
                available=name in present,
                derived=False,
            )
        )

    # AOV is a derived business concept, not a source column.
    concepts.append(
        BusinessConcept(
            name="aov",
            label="Average Order Value (AOV)",
            kind="metric",
            source_columns=[],
            available=_derive_aov_available(
                present
            ),
            derived=True,
        )
    )

    available = {
        concept.name: concept
        for concept in concepts
        if concept.available
    }

    dimensions = [
        concept.name
        for concept in available.values()
        if concept.kind == "dimension"
    ]

    metrics = [
        concept.name
        for concept in available.values()
        if concept.kind == "metric"
    ]

    capabilities = {
        "sales_performance": (
            "revenue" in available
            and "order_id" in available
        ),
        "product_analysis": (
            "product" in available
            and "revenue" in available
        ),
        "customer_analysis": (
            "customer" in available
            and "revenue" in available
        ),
        "monthly_analysis": (
            "date" in available
            and "revenue" in available
        ),
        "discount_analysis": (
            "discount_pct" in available
            or "discount_amount" in available
        ),
        "return_analysis": (
            "return_status" in available
            or "return_amount" in available
        ),
        "regional_analysis": (
            "region" in available
        ),
        "sales_team_analysis": (
            "salesperson" in available
        ),
        "channel_analysis": (
            "channel" in available
        ),
        "payment_analysis": (
            "payment_method" in available
        ),
        "order_status_analysis": (
            "order_status" in available
        ),
        "profitability_analysis": (
            "cost" in available
            and "revenue" in available
        ),
    }

    return {
        "concepts": [
            asdict(concept)
            for concept in concepts
        ],
        "available_concepts": list(
            available.keys()
        ),
        "dimensions": dimensions,
        "metrics": metrics,
        "capabilities": capabilities,
    }


def explain_semantic_model(
    model: dict[str, Any]
) -> dict[str, Any]:

    concepts = model.get(
        "concepts",
        []
    )

    core = [
        concept
        for concept in concepts
        if concept["name"]
        in CORE_CONCEPTS
        and concept["available"]
    ]

    optional = [
        concept
        for concept in concepts
        if concept["name"]
        in OPTIONAL_CONCEPTS
        and concept["available"]
    ]

    derived = [
        concept
        for concept in concepts
        if concept["derived"]
        and concept["available"]
    ]

    capabilities = [
        name
        for name, available in model.get(
            "capabilities",
            {}
        ).items()
        if available
    ]

    return {
        "core": core,
        "optional": optional,
        "derived": derived,
        "capabilities": capabilities,
    }
