
"""
Business Intelligence Engine v2

Deterministic analysis layer:
    verified metrics -> findings -> scoring/ranking -> AI explanation

The engine deliberately does not invent causes. It identifies measurable
patterns from the verified report and assigns a transparent priority score.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


# -------------------------
# Configurable thresholds
# -------------------------

REVENUE_DROP_THRESHOLD = 0.20
REVENUE_GROWTH_THRESHOLD = 0.20

TOP_PRODUCT_CONCENTRATION_THRESHOLD = 0.25
TOP_PRODUCT_HIGH_CONCENTRATION_THRESHOLD = 0.35

CUSTOMER_CONCENTRATION_THRESHOLD = 0.15
CUSTOMER_HIGH_CONCENTRATION_THRESHOLD = 0.25

VOLUME_REVENUE_GAP_THRESHOLD = 0.10
VOLUME_REVENUE_HIGH_GAP_THRESHOLD = 0.20

TOP_FINDINGS_LIMIT = 3
TOP_POSITIVE_FINDINGS_LIMIT = 2


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None

    return (current - previous) / previous


def _severity_from_score(score: float) -> str:
    if score >= 85:
        return "high"

    if score >= 50:
        return "medium"

    return "low"


def _sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort by priority score, then by severity."""
    severity_rank = {
        "high": 3,
        "medium": 2,
        "low": 1
    }

    return sorted(
        findings,
        key=lambda finding: (
            finding.get("priority_score", 0),
            severity_rank.get(
                finding.get("severity", "low"),
                0
            )
        ),
        reverse=True
    )



def _product_metric_contribution(
    previous_rows: pd.DataFrame,
    current_rows: pd.DataFrame,
) -> dict[str, Any]:
    """
    Explain product-level movement for revenue, orders and items.

    Revenue uses sum(revenue).
    Orders use unique order_id when available.
    Items use sum(quantity) when available.
    """
    result = {
        "revenue_drags": [],
        "revenue_offsets": [],
        "order_drags": [],
        "order_offsets": [],
        "item_drags": [],
        "item_offsets": [],
    }

    if (
        previous_rows is None
        or current_rows is None
    ):
        return result

    if (
        "product" not in previous_rows.columns
        or "product" not in current_rows.columns
    ):
        return result

    previous_product = (
        previous_rows.groupby("product", dropna=True)
    )
    current_product = (
        current_rows.groupby("product", dropna=True)
    )

    # Revenue movement.
    if (
        "revenue" in previous_rows.columns
        and "revenue" in current_rows.columns
    ):
        previous_revenue = previous_product["revenue"].sum()
        current_revenue = current_product["revenue"].sum()

        revenue_change = (
            current_revenue
            .sub(previous_revenue, fill_value=0)
        )

        for product_name, delta in revenue_change.items():

            delta = _safe_float(delta)

            if delta < 0:
                result["revenue_drags"].append({
                    "product": str(product_name),
                    "change": delta,
                    "abs_change": abs(delta),
                })
            elif delta > 0:
                result["revenue_offsets"].append({
                    "product": str(product_name),
                    "change": delta,
                    "abs_change": delta,
                })

    # Order movement.
    if (
        "order_id" in previous_rows.columns
        and "order_id" in current_rows.columns
    ):
        previous_orders = previous_product["order_id"].nunique()
        current_orders = current_product["order_id"].nunique()

        order_change = (
            current_orders
            .sub(previous_orders, fill_value=0)
        )

        for product_name, delta in order_change.items():

            delta = _safe_float(delta)

            if delta < 0:
                result["order_drags"].append({
                    "product": str(product_name),
                    "change": delta,
                    "abs_change": abs(delta),
                })
            elif delta > 0:
                result["order_offsets"].append({
                    "product": str(product_name),
                    "change": delta,
                    "abs_change": delta,
                })

    # Item movement.
    if (
        "quantity" in previous_rows.columns
        and "quantity" in current_rows.columns
    ):
        previous_items = previous_product["quantity"].sum()
        current_items = current_product["quantity"].sum()

        item_change = (
            current_items
            .sub(previous_items, fill_value=0)
        )

        for product_name, delta in item_change.items():

            delta = _safe_float(delta)

            if delta < 0:
                result["item_drags"].append({
                    "product": str(product_name),
                    "change": delta,
                    "abs_change": abs(delta),
                })
            elif delta > 0:
                result["item_offsets"].append({
                    "product": str(product_name),
                    "change": delta,
                    "abs_change": delta,
                })

    for key in (
        "revenue_drags",
        "revenue_offsets",
        "order_drags",
        "order_offsets",
        "item_drags",
        "item_offsets",
    ):
        result[key] = sorted(
            result[key],
            key=lambda item: item["abs_change"],
            reverse=True
        )[:3]

    return result


def _format_metric_contribution(
    metric_items: list[dict[str, Any]],
    decimals: int = 0,
) -> str:
    """Format a product contribution list."""
    if not metric_items:
        return ""

    formatted = []

    for item in metric_items:

        change = item["change"]

        if decimals == 2:
            value = f"{change:+,.2f}"
        else:
            value = f"{change:+,.0f}"

        formatted.append(
            f"{item['product']} {value}"
        )

    return "; ".join(formatted)


def _format_product_contribution(
    contribution: dict[str, Any],
) -> str:
    """Format revenue/product contribution for backward compatibility."""

    parts = []

    revenue_drags = contribution.get(
        "revenue_drags",
        []
    )

    revenue_offsets = contribution.get(
        "revenue_offsets",
        []
    )

    if revenue_drags:

        parts.append(
            "Revenue drags: "
            + _format_metric_contribution(
                revenue_drags,
                decimals=2
            )
        )

    if revenue_offsets:

        parts.append(
            "Revenue offsets: "
            + _format_metric_contribution(
                revenue_offsets,
                decimals=2
            )
        )

    return " | ".join(parts)



def analyze_monthly_changes(
    monthly: pd.DataFrame,
    sales_data: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    """
    Detect material month-over-month revenue changes and decompose
    the movement into orders, items, and average order value (AOV).
    """
    findings: list[dict[str, Any]] = []

    if monthly is None or monthly.empty:
        return findings

    ordered = monthly.sort_index()

    if "revenue" not in ordered.columns:
        return findings

    period_change_findings: list[dict[str, Any]] = []

    for index in range(1, len(ordered)):

        current_period = ordered.index[index]
        previous_period = ordered.index[index - 1]

        current_revenue = _safe_float(
            ordered.iloc[index]["revenue"]
        )
        previous_revenue = _safe_float(
            ordered.iloc[index - 1]["revenue"]
        )

        change = _pct_change(
            current_revenue,
            previous_revenue
        )

        if change is None:
            continue

        change_pct = change * 100

        current_orders = None
        previous_orders = None

        current_quantity = None
        previous_quantity = None

        current_aov = None
        previous_aov = None

        order_change = None
        quantity_change = None
        aov_change = None

        if (
            sales_data is not None
            and not sales_data.empty
            and "order_id" in sales_data.columns
            and "date" in sales_data.columns
        ):

            current_rows = sales_data[
                sales_data["date"].dt.to_period("M")
                == current_period
            ]

            previous_rows = sales_data[
                sales_data["date"].dt.to_period("M")
                == previous_period
            ]

            current_orders = int(
                current_rows["order_id"].nunique()
            )

            previous_orders = int(
                previous_rows["order_id"].nunique()
            )

            order_change = _pct_change(
                current_orders,
                previous_orders
            )

            if "quantity" in sales_data.columns:

                current_quantity = _safe_float(
                    current_rows["quantity"].sum()
                )

                previous_quantity = _safe_float(
                    previous_rows["quantity"].sum()
                )

                quantity_change = _pct_change(
                    current_quantity,
                    previous_quantity
                )

            if current_orders > 0:
                current_aov = (
                    current_revenue / current_orders
                )

            if previous_orders > 0:
                previous_aov = (
                    previous_revenue / previous_orders
                )

            if (
                current_aov is not None
                and previous_aov is not None
            ):
                aov_change = _pct_change(
                    current_aov,
                    previous_aov
                )

        def describe_change(
            value: float | None,
            positive_word: str,
            negative_word: str,
        ) -> str:

            if value is None:
                return "not available"

            if value >= 0:
                return (
                    f"{positive_word} {value * 100:.1f}%"
                )

            return (
                f"{negative_word} {abs(value) * 100:.1f}%"
            )

        if change <= -REVENUE_DROP_THRESHOLD:

            score = min(
                99.9,
                70 + (abs(change_pct) * 0.85)
            )

            product_contribution = _product_metric_contribution(
                previous_rows,
                current_rows,
            )

            product_contribution_text = _format_product_contribution(
                product_contribution
            )

            driver = "revenue movement"

            if (
                aov_change is not None
                and aov_change <= -0.10
                and (
                    order_change is None
                    or abs(aov_change) > abs(order_change)
                )
            ):

                driver = "average order value"

            elif (
                order_change is not None
                and order_change <= -0.10
                and (
                    aov_change is None
                    or abs(order_change) > abs(aov_change)
                )
            ):

                driver = "order volume"

            elif (
                order_change is not None
                and order_change < 0
                and aov_change is not None
                and aov_change < 0
            ):

                driver = "both order volume and average order value"

            if driver == "order volume":

                driver_product_items = product_contribution.get(
                    "order_drags",
                    []
                )

                driver_product_text = _format_metric_contribution(
                    driver_product_items
                )

            elif driver == "average order value":

                driver_product_items = product_contribution.get(
                    "revenue_drags",
                    []
                )

                driver_product_text = _format_metric_contribution(
                    driver_product_items,
                    decimals=2
                )

            elif driver == "both order volume and average order value":

                driver_product_items = product_contribution.get(
                    "order_drags",
                    []
                )

                driver_product_text = _format_metric_contribution(
                    driver_product_items
                )

            else:

                driver_product_text = product_contribution_text

            revenue_line = (
                f"Revenue: ${previous_revenue:,.2f} → "
                f"${current_revenue:,.2f} "
                f"({change_pct:.1f}%)"
            )

            order_line = ""

            if (
                current_orders is not None
                and previous_orders is not None
                and order_change is not None
            ):
                order_line = (
                    f"Orders: {previous_orders:,} → "
                    f"{current_orders:,} "
                    f"({order_change * 100:.1f}%)"
                )

            aov_line = ""

            if (
                current_aov is not None
                and previous_aov is not None
                and aov_change is not None
            ):
                aov_line = (
                    f"AOV: ${previous_aov:,.2f} → "
                    f"${current_aov:,.2f} "
                    f"({aov_change * 100:.1f}%)"
                )

            quantity_line = ""

            if (
                current_quantity is not None
                and previous_quantity is not None
                and quantity_change is not None
            ):
                quantity_line = (
                    f"Items: {previous_quantity:,.0f} → "
                    f"{current_quantity:,.0f} "
                    f"({quantity_change * 100:.1f}%)"
                )

            breakdown = [
                line
                for line in [
                    revenue_line,
                    order_line,
                    aov_line,
                    quantity_line
                ]
                if line
            ]

            what_happened = (
                f"Revenue fell {abs(change_pct):.1f}% from "
                f"{previous_period} to {current_period}. "
                + " | ".join(breakdown)
            )

            if driver == "average order value":
                why_it_matters = (
                    "Revenue declined much faster at the order-value level "
                    "than at the transaction-volume level. "
                    "The primary measurable driver is lower AOV."
                )

            elif driver == "order volume":
                why_it_matters = (
                    "Revenue declined mainly alongside lower transaction "
                    "volume. The primary measurable driver is fewer orders."
                )

            elif driver == "both order volume and average order value":
                why_it_matters = (
                    "Both transaction volume and order value moved down, "
                    "so the decline has two measurable components."
                )

            else:
                why_it_matters = (
                    "The available metrics show a material revenue decline, "
                    "but they do not isolate a single measurable driver."
                )

            investigate_next = (
                f"Investigate the {driver} change between "
                f"{previous_period} and {current_period}. "
                "Review product-level revenue movement next. "
                "The sales data does not establish the operational cause."
            )

            period_change_findings.append({
                "type": "revenue_drop",
                "direction": "risk",
                "period": str(current_period),
                "previous_period": str(previous_period),
                "current_revenue": current_revenue,
                "previous_revenue": previous_revenue,
                "change_pct": change_pct,
                "current_orders": current_orders,
                "previous_orders": previous_orders,
                "order_change_pct": (
                    order_change * 100
                    if order_change is not None
                    else None
                ),
                "current_quantity": current_quantity,
                "previous_quantity": previous_quantity,
                "quantity_change_pct": (
                    quantity_change * 100
                    if quantity_change is not None
                    else None
                ),
                "current_aov": current_aov,
                "previous_aov": previous_aov,
                "aov_change_pct": (
                    aov_change * 100
                    if aov_change is not None
                    else None
                ),
                "primary_driver": driver,
                "product_contribution": product_contribution,
                "product_contribution_text": product_contribution_text,
                "driver_product_text": driver_product_text,
                "priority_score": score,
                "severity": _severity_from_score(score),
                "message": (
                    f"Revenue fell {abs(change_pct):.1f}% "
                    f"from {previous_period} to {current_period}."
                ),
                "business_context": why_it_matters,
                "what_happened": what_happened,
                "why_it_matters": why_it_matters,
                "investigate_next": investigate_next,
            })

        elif change >= REVENUE_GROWTH_THRESHOLD:

            magnitude_score = min(
                int(change_pct * 1.5),
                60
            )

            score = 25 + magnitude_score

            product_contribution = _product_metric_contribution(
                previous_rows,
                current_rows,
            )

            product_contribution_text = _format_product_contribution(
                product_contribution
            )

            driver = "revenue movement"

            if (
                aov_change is not None
                and aov_change >= 0.10
                and (
                    order_change is None
                    or abs(aov_change) > abs(order_change)
                )
            ):
                driver = "average order value"

            elif (
                order_change is not None
                and order_change >= 0.10
                and (
                    aov_change is None
                    or abs(order_change) > abs(aov_change)
                )
            ):
                driver = "order volume"

            elif (
                order_change is not None
                and order_change > 0
                and aov_change is not None
                and aov_change > 0
            ):
                driver = "both order volume and average order value"

            if driver == "order volume":

                driver_product_items = product_contribution.get(
                    "order_offsets",
                    []
                )

                driver_product_text = _format_metric_contribution(
                    driver_product_items
                )

            elif driver == "average order value":

                driver_product_items = product_contribution.get(
                    "revenue_offsets",
                    []
                )

                driver_product_text = _format_metric_contribution(
                    driver_product_items,
                    decimals=2
                )

            elif driver == "both order volume and average order value":

                driver_product_items = product_contribution.get(
                    "order_offsets",
                    []
                )

                driver_product_text = _format_metric_contribution(
                    driver_product_items
                )

            else:

                driver_product_text = product_contribution_text

            revenue_line = (
                f"Revenue: ${previous_revenue:,.2f} → "
                f"${current_revenue:,.2f} "
                f"(+{change_pct:.1f}%)"
            )

            order_line = ""

            if (
                current_orders is not None
                and previous_orders is not None
                and order_change is not None
            ):
                order_line = (
                    f"Orders: {previous_orders:,} → "
                    f"{current_orders:,} "
                    f"({order_change * 100:+.1f}%)"
                )

            aov_line = ""

            if (
                current_aov is not None
                and previous_aov is not None
                and aov_change is not None
            ):
                aov_line = (
                    f"AOV: ${previous_aov:,.2f} → "
                    f"${current_aov:,.2f} "
                    f"({aov_change * 100:+.1f}%)"
                )

            quantity_line = ""

            if (
                current_quantity is not None
                and previous_quantity is not None
                and quantity_change is not None
            ):
                quantity_line = (
                    f"Items: {previous_quantity:,.0f} → "
                    f"{current_quantity:,.0f} "
                    f"({quantity_change * 100:+.1f}%)"
                )

            breakdown = [
                line
                for line in [
                    revenue_line,
                    order_line,
                    aov_line,
                    quantity_line
                ]
                if line
            ]

            what_happened = (
                f"Revenue increased {change_pct:.1f}% from "
                f"{previous_period} to {current_period}. "
                + " | ".join(breakdown)
            )

            why_it_matters = (
                f"The measurable change was led primarily by "
                f"{driver}, which is worth reviewing for repeatable patterns."
            )

            investigate_next = (
                f"Compare the {driver} and product mix between "
                f"{previous_period} and {current_period}. "
                "The sales data does not establish the operational cause."
            )

            period_change_findings.append({
                "type": "revenue_growth",
                "direction": "positive",
                "period": str(current_period),
                "previous_period": str(previous_period),
                "current_revenue": current_revenue,
                "previous_revenue": previous_revenue,
                "change_pct": change_pct,
                "current_orders": current_orders,
                "previous_orders": previous_orders,
                "order_change_pct": (
                    order_change * 100
                    if order_change is not None
                    else None
                ),
                "current_quantity": current_quantity,
                "previous_quantity": previous_quantity,
                "quantity_change_pct": (
                    quantity_change * 100
                    if quantity_change is not None
                    else None
                ),
                "current_aov": current_aov,
                "previous_aov": previous_aov,
                "aov_change_pct": (
                    aov_change * 100
                    if aov_change is not None
                    else None
                ),
                "primary_driver": driver,
                "product_contribution": product_contribution,
                "product_contribution_text": product_contribution_text,
                "driver_product_text": driver_product_text,
                "priority_score": score,
                "severity": _severity_from_score(score),
                "message": (
                    f"Revenue increased {change_pct:.1f}% "
                    f"from {previous_period} to {current_period}."
                ),
                "business_context": why_it_matters,
                "what_happened": what_happened,
                "why_it_matters": why_it_matters,
                "investigate_next": investigate_next,
            })

    negative = [
        finding
        for finding in period_change_findings
        if finding.get("type") == "revenue_drop"
    ]

    if negative:

        largest = max(
            negative,
            key=lambda finding: abs(
                _safe_float(
                    finding.get("change_pct")
                )
            )
        )

        largest["is_largest_decline"] = True

        largest["why_it_matters"] = (
            largest["why_it_matters"]
            + " It is the largest month-over-month revenue decline "
            "in the selected reporting period."
        )

        largest["business_context"] = (
            largest["why_it_matters"]
        )

    return period_change_findings



def analyze_product_mix(
    products: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Detect product concentration and volume/revenue mix differences."""
    findings: list[dict[str, Any]] = []

    if products is None or products.empty:
        return findings

    if "revenue" not in products.columns:
        return findings

    ordered = products.sort_values(
        "revenue",
        ascending=False
    )

    total_revenue = _safe_float(
        ordered["revenue"].sum()
    )

    if total_revenue <= 0:
        return findings

    top_product = ordered.iloc[0]
    top_product_name = str(ordered.index[0])

    top_product_revenue = _safe_float(
        top_product["revenue"]
    )

    top_product_share = (
        top_product_revenue / total_revenue
    )

    if top_product_share >= TOP_PRODUCT_HIGH_CONCENTRATION_THRESHOLD:

        score = 72

        findings.append({
            "type": "product_concentration",
            "direction": "risk",
            "product": top_product_name,
            "revenue": top_product_revenue,
            "revenue_share_pct": top_product_share * 100,
            "priority_score": score,
            "severity": "high",
            "message": (
                f"{top_product_name} contributes "
                f"{top_product_share * 100:.1f}% of total revenue."
            ),
            "business_context": (
                "A large share of revenue is concentrated in one product, "
                "which makes that product particularly important to monitor."
            ),
            "what_happened": (
                f"{top_product_name} generated "
                f"${top_product_revenue:,.2f}, representing "
                f"{top_product_share * 100:.1f}% of total revenue."
            ),
            "why_it_matters": (
                "This product has an outsized influence on total revenue, "
                "so changes in its sales can materially affect overall results."
            ),
            "investigate_next": (
                "Review the product's monthly sales trend and its order volume "
                "to understand whether the concentration is stable or changing."
            ),
        })

    elif top_product_share >= TOP_PRODUCT_CONCENTRATION_THRESHOLD:

        score = 50

        findings.append({
            "type": "product_concentration",
            "direction": "risk",
            "product": top_product_name,
            "revenue": top_product_revenue,
            "revenue_share_pct": top_product_share * 100,
            "priority_score": score,
            "severity": "medium",
            "message": (
                f"{top_product_name} contributes "
                f"{top_product_share * 100:.1f}% of total revenue."
            ),
            "business_context": (
                "The product represents a meaningful share of revenue and "
                "deserves monitoring as part of the overall product mix."
            ),
            "what_happened": (
                f"{top_product_name} generated "
                f"${top_product_revenue:,.2f}, representing "
                f"{top_product_share * 100:.1f}% of total revenue."
            ),
            "why_it_matters": (
                "The product has a meaningful effect on overall revenue "
                "and should be monitored as part of the product mix."
            ),
            "investigate_next": (
                "Compare this product's revenue trend with the other products "
                "to see whether its share is increasing or declining."
            ),
        })

    if "quantity_sold" in ordered.columns:

        total_quantity = _safe_float(
            ordered["quantity_sold"].sum()
        )

        if total_quantity > 0:

            for product_name, row in ordered.iterrows():

                product_quantity = _safe_float(
                    row["quantity_sold"]
                )

                product_revenue = _safe_float(
                    row["revenue"]
                )

                quantity_share = (
                    product_quantity / total_quantity
                )

                revenue_share = (
                    product_revenue / total_revenue
                )

                gap = quantity_share - revenue_share

                if gap >= VOLUME_REVENUE_HIGH_GAP_THRESHOLD:
                    score = 76
                    severity = "high"

                elif gap >= VOLUME_REVENUE_GAP_THRESHOLD:
                    score = 52
                    severity = "medium"

                else:
                    continue

                findings.append({
                    "type": "high_volume_low_revenue_share",
                    "direction": "risk",
                    "product": str(product_name),
                    "quantity_share_pct": quantity_share * 100,
                    "revenue_share_pct": revenue_share * 100,
                    "gap_pct_points": gap * 100,
                    "priority_score": score,
                    "severity": severity,
                    "message": (
                        f"{product_name} contributes "
                        f"{quantity_share * 100:.1f}% of item volume "
                        f"but only {revenue_share * 100:.1f}% of revenue."
                    ),
                    "business_context": (
                        "The product has a larger share of unit volume than "
                        "revenue, which may justify reviewing its role in the "
                        "product mix. Profitability cannot be inferred from "
                        "the available data."
                    ),
                    "what_happened": (
                        f"{product_name} contributes "
                        f"{quantity_share * 100:.1f}% of item volume "
                        f"but {revenue_share * 100:.1f}% of revenue."
                    ),
                    "why_it_matters": (
                        "A relatively large share of unit volume is producing "
                        "a smaller share of revenue, making the product mix "
                        "worth reviewing."
                    ),
                    "investigate_next": (
                        "Compare the product's order count, revenue per order, "
                        "and trend against other products. Profitability cannot "
                        "be inferred from the available data."
                    ),
                })

    return findings


def analyze_customer_concentration(
    customers: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Detect material customer revenue concentration."""
    findings: list[dict[str, Any]] = []

    if customers is None or customers.empty:
        return findings

    if "revenue" not in customers.columns:
        return findings

    ordered = customers.sort_values(
        "revenue",
        ascending=False
    )

    total_revenue = _safe_float(
        ordered["revenue"].sum()
    )

    if total_revenue <= 0:
        return findings

    top_customer = ordered.iloc[0]

    top_customer_name = str(
        ordered.index[0]
    )

    top_customer_revenue = _safe_float(
        top_customer["revenue"]
    )

    share = (
        top_customer_revenue / total_revenue
    )

    if share >= CUSTOMER_HIGH_CONCENTRATION_THRESHOLD:

        score = 68
        severity = "medium"

    elif share >= CUSTOMER_CONCENTRATION_THRESHOLD:

        score = 48
        severity = "medium"

    else:
        return findings

    findings.append({
        "type": "customer_concentration",
        "direction": "risk",
        "customer": top_customer_name,
        "revenue": top_customer_revenue,
        "revenue_share_pct": share * 100,
        "priority_score": score,
        "severity": severity,
        "message": (
            f"{top_customer_name} contributes "
            f"{share * 100:.1f}% of total revenue."
        ),
        "business_context": (
            "A meaningful share of revenue comes from one customer, "
            "so changes in that customer's activity are important to monitor."
        ),
        "what_happened": (
            f"{top_customer_name} generated "
            f"${top_customer_revenue:,.2f}, representing "
            f"{share * 100:.1f}% of total revenue."
        ),
        "why_it_matters": (
            "A meaningful share of revenue is concentrated in one customer, "
            "so changes in that customer's activity can affect total revenue."
        ),
        "investigate_next": (
            "Review this customer's order and revenue trend and compare it "
            "with the broader customer base. Do not infer retention or churn "
            "without additional data."
        ),
    })

    return findings


def _add_action_plan(finding: dict[str, Any]) -> dict[str, Any]:
    finding = dict(finding)

    if finding.get("recommended_action"):
        return finding

    kind = finding.get("type")

    if kind == "revenue_drop":
        driver = finding.get("primary_driver", "revenue movement")
        period = finding.get("period", "the latest period")
        finding["recommended_action"] = (
            f"Break down the {driver} change in {period} by product and customer, "
            "then confirm the operational cause before taking corrective action."
        )
        finding["decision_question"] = (
            "Which product, customer, or region contributed most to the decline?"
        )

    elif kind == "revenue_growth":
        driver = finding.get("primary_driver", "revenue movement")
        period = finding.get("period", "the latest period")
        finding["recommended_action"] = (
            f"Identify what drove the {driver} improvement in {period} and "
            "check whether the pattern is repeatable before scaling it."
        )
        finding["decision_question"] = (
            "What specifically drove the improvement, and can we reproduce it?"
        )

    elif kind == "product_concentration":
        product = finding.get("product", "the leading product")
        finding["recommended_action"] = (
            f"Review {product}'s inventory, pricing, margin, and customer mix, "
            "and identify one or two products that could diversify revenue."
        )
        finding["decision_question"] = (
            f"Which customers and months are driving {product}'s revenue?"
        )

    elif kind == "high_volume_low_revenue_share":
        product = finding.get("product", "the product")
        finding["recommended_action"] = (
            f"Review {product}'s price, discounting, order mix, and role in the "
            "portfolio. Do not assume low profitability without cost data."
        )
        finding["decision_question"] = (
            f"How has {product}'s revenue and volume changed over time?"
        )

    elif kind == "customer_concentration":
        customer = finding.get("customer", "the leading customer")
        finding["recommended_action"] = (
            f"Review {customer}'s order and revenue trend, assess account "
            "dependency, and identify opportunities to diversify the customer base."
        )
        finding["decision_question"] = (
            f"Which products and periods generate the most revenue from {customer}?"
        )

    else:
        finding.setdefault(
            "recommended_action",
            "Drill into the supporting dimensions before making a business decision.",
        )
        finding.setdefault(
            "decision_question",
            "What product, customer, period, or segment is driving this finding?",
        )

    return finding


def build_business_findings(
    report: dict[str, Any],
) -> dict[str, Any]:
    """
    Build, score, and rank deterministic business findings.
    """

    products = report.get("products")
    customers = report.get("customers")
    monthly = report.get("monthly")

    monthly_findings = analyze_monthly_changes(
        monthly,
        report.get("data")
    )

    product_findings = analyze_product_mix(
        products
    )

    customer_findings = analyze_customer_concentration(
        customers
    )

    all_findings = (
        monthly_findings
        + product_findings
        + customer_findings
    )

    all_findings = [
        _add_action_plan(finding)
        for finding in all_findings
    ]

    ranked_findings = _sort_findings(
        all_findings
    )

    # Priority attention is intentionally limited to negative/risk findings.
    # Positive movements are shown separately so they do not displace risks.
    risk_findings = [
        finding
        for finding in ranked_findings
        if finding.get("direction") == "risk"
    ]

    positive_findings = [
        finding
        for finding in ranked_findings
        if finding.get("direction") == "positive"
    ]

    return {
        "findings": ranked_findings,
        "priority_findings": risk_findings[
            :TOP_FINDINGS_LIMIT
        ],
        "positive_findings": positive_findings[
            :TOP_POSITIVE_FINDINGS_LIMIT
        ],
        "other_findings_count": max(
            len(ranked_findings) - TOP_FINDINGS_LIMIT,
            0
        ),
        "finding_count": len(ranked_findings),
        "high_priority": [
            finding
            for finding in ranked_findings
            if finding.get("severity") == "high"
        ],
    }
