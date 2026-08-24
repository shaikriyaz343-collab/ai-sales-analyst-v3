
from __future__ import annotations

import calendar
import json
import os
import re
from typing import Any

import pandas as pd


MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

ALLOWED_OPERATIONS = {
    "rank",
    "aggregate",
    "compare",
    "explain_change",
    "trend",
    "lookup",
    "contribution",
}

ALLOWED_ENTITIES = {
    "business",
    "product",
    "customer",
    "month",
}

ALLOWED_METRICS = {
    "revenue",
    "orders",
    "quantity",
    "aov",
    "revenue_share",
    "return_rate",
}


def _safe_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _month_number(value: Any) -> int | None:
    if value is None:
        return None

    if isinstance(value, int):
        return value if 1 <= value <= 12 else None

    text = str(value).strip().lower()

    if text.isdigit():
        number = int(text)
        return number if 1 <= number <= 12 else None

    return MONTH_MAP.get(text)


def _default_year(report) -> int | None:
    data = report.get("data")

    if data is None or data.empty:
        return None

    return int(data["date"].dt.year.max())


def _month_filter(data: pd.DataFrame, month: int, year: int | None):
    if year is None:
        year = int(data["date"].dt.year.max())

    return data[
        (data["date"].dt.month == month)
        & (data["date"].dt.year == year)
    ].copy()


def _metric_from_rows(rows: pd.DataFrame, metric: str) -> float | None:
    if rows is None or rows.empty:
        return None

    if metric == "revenue":
        return _safe_float(rows["revenue"].sum())

    if metric == "orders":
        return int(rows["order_id"].nunique())

    if metric == "quantity":
        return _safe_float(rows["quantity"].sum())

    if metric == "aov":
        orders = rows["order_id"].nunique()
        if orders == 0:
            return None
        return float(rows["revenue"].sum()) / orders

    if metric == "return_rate":
        if "return_status" not in rows.columns:
            return None
        total_orders = rows["order_id"].nunique()
        if total_orders == 0:
            return None
        returned_mask = rows["return_status"].astype(str).str.lower().str.strip().isin(['returned', 'yes', 'true', '1'])
        returned_orders = rows[returned_mask]["order_id"].nunique()
        return (returned_orders / total_orders) * 100.0

    return None


def _format_metric(metric: str, value: float | None) -> str:
    if value is None:
        return "not available"

    if metric == "revenue":
        return f"${value:,.2f}"

    if metric == "aov":
        return f"${value:,.2f}"

    if metric == "revenue_share":
        return f"{value:.2f}%"

    if metric == "return_rate":
        return f"{value:.1f}%"

    return f"{value:,.0f}"


def _default_metric(question: str) -> str:
    q = question.lower()

    if any(
        phrase in q
        for phrase in (
            "sold the most",
            "sold most",
            "most units",
            "most items",
            "highest units",
            "highest quantity",
            "most quantity",
        )
    ):
        return "quantity"

    if any(
        phrase in q
        for phrase in (
            "most orders",
            "highest orders",
            "order count",
            "number of orders",
        )
    ):
        return "orders"

    if any(
        phrase in q
        for phrase in (
            "average order value",
            "aov",
            "revenue per order",
            "average order",
        )
    ):
        return "aov"

    if any(
        phrase in q
        for phrase in (
            "share",
            "percentage of revenue",
            "percent of revenue",
        )
    ):
        return "revenue_share"

    if any(
        phrase in q
        for phrase in (
            "return rate",
            "refund rate",
            "returned",
            "refunded",
            "returns",
        )
    ):
        return "return_rate"

    return "revenue"


def _fallback_time_scope(question: str) -> dict[str, Any]:
    q = question.lower()

    months = []

    for name, number in sorted(
        MONTH_MAP.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if re.search(
            rf"\b{re.escape(name)}\b",
            q,
        ):
            if number not in months:
                months.append(number)

    year_match = re.search(
        r"\b(20\d{2})\b",
        q,
    )

    year = int(year_match.group(1)) if year_match else None

    if len(months) >= 2:
        return {
            "type": "comparison",
            "month_start": months[0],
            "month_end": months[1],
            "year": year,
        }

    if len(months) == 1:
        return {
            "type": "month",
            "month": months[0],
            "year": year,
        }

    return {
        "type": "period",
        "year": year,
    }


def _fallback_plan(report, question: str) -> dict[str, Any]:
    q = question.lower()

    time_scope = _fallback_time_scope(question)

    if "customer" in q or "buyer" in q or "client" in q:
        entity = "customer"
    elif "product" in q or "item" in q or "sku" in q:
        entity = "product"
    elif "month" in q or "monthly" in q:
        entity = "month"
    else:
        entity = "business"

    metric = _default_metric(question)

    if any(
        phrase in q
        for phrase in (
            "why was",
            "why did",
            "why is",
            "why were",
            "what caused",
            "cause of",
            "caused the decline",
            "caused the drop",
        )
    ):
        operation = "explain_change"
    elif (
        "compare" in q
        or "compared with" in q
        or "compared to" in q
        or "difference between" in q
        or time_scope["type"] == "comparison"
    ):
        operation = "compare"
    elif (
        "trend" in q
        or "over time" in q
        or "monthly performance" in q
    ):
        operation = "trend"
    elif (
        "contribute" in q
        or "caused the decline" in q
        or "drove the decline" in q
    ):
        operation = "contribution"
    elif any(
        phrase in q
        for phrase in (
            "best",
            "top",
            "highest",
            "lowest",
            "worst",
            "most",
            "least",
            "sold the most",
        )
    ):
        operation = "rank"
    elif any(
        phrase in q
        for phrase in (
            "how much",
            "what was",
            "what is",
            "total",
        )
    ):
        operation = "aggregate"
    else:
        operation = "lookup"

    ranking = "lowest" if any(
        phrase in q
        for phrase in (
            "lowest",
            "worst",
            "least",
        )
    ) else "highest"

    filters = {
        "product": None,
        "customer": None,
    }

    return {
        "operation": operation,
        "entity": entity,
        "metric": metric,
        "ranking": ranking,
        "limit": 1,
        "time_scope": time_scope,
        "filters": filters,
        "comparison_metric": [
            "revenue",
            "orders",
            "quantity",
            "aov",
        ]
        if operation in {"compare", "explain_change"}
        else [metric],
        "use_business_findings": operation in {
            "explain_change",
            "contribution",
        },
    }


def _llm_plan(report, question: str) -> dict[str, Any] | None:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    data = report.get("data")

    available_products = sorted(
        data["product"].dropna().astype(str).unique().tolist()
    ) if data is not None and not data.empty else []

    available_customers = sorted(
        data["customer"].dropna().astype(str).unique().tolist()
    ) if data is not None and not data.empty else []

    prompt = f"""
You are the query-planning component of an AI sales analyst.

Convert the user's natural-language question into a structured query plan.
DO NOT answer the question.

USER QUESTION:
{question}

AVAILABLE PRODUCTS:
{available_products}

AVAILABLE CUSTOMERS:
{available_customers}

ALLOWED OPERATIONS:
rank, aggregate, compare, explain_change, trend, lookup, contribution

ALLOWED ENTITIES:
business, product, customer, month

ALLOWED METRICS:
revenue, orders, quantity, aov, revenue_share

RULES:
1. Identify what the user wants, even when they use informal wording.
2. "best product" normally means highest revenue unless they explicitly
   ask for units/items/orders.
3. "sold the most" means highest quantity.
4. "top customer" normally means highest revenue unless the user asks for
   orders or units.
5. Preserve any named month, year, product, or customer.
6. If two months are named, use a comparison time_scope.
7. A "why was X weak" question should use explain_change and compare X
   against the immediately preceding month when that is the natural context.
8. If the question asks which products contributed to a decline, use
   contribution.
9. Never invent a product or customer not present in the available lists.
10. If the question is ambiguous, choose the most natural interpretation
    and mark confidence as "medium".

Return ONLY JSON matching this schema:
{{
  "operation": "rank|aggregate|compare|explain_change|trend|lookup|contribution",
  "entity": "business|product|customer|month",
  "metric": "revenue|orders|quantity|aov|revenue_share",
  "ranking": "highest|lowest",
  "limit": 1,
  "time_scope": {{
      "type": "period|month|date_range|comparison",
      "month": null,
      "month_start": null,
      "month_end": null,
      "year": null
  }},
  "filters": {{
      "product": null,
      "customer": null
  }},
  "comparison_metric": [
      "revenue"
  ],
  "use_business_findings": false,
  "confidence": "high|medium|low"
}}
"""

    try:
        from google import genai

        client = genai.Client(
            api_key=api_key
        )

        schema = {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": sorted(ALLOWED_OPERATIONS),
                },
                "entity": {
                    "type": "string",
                    "enum": sorted(ALLOWED_ENTITIES),
                },
                "metric": {
                    "type": "string",
                    "enum": sorted(ALLOWED_METRICS),
                },
                "ranking": {
                    "type": "string",
                    "enum": ["highest", "lowest"],
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                },
                "time_scope": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "period",
                                "month",
                                "date_range",
                                "comparison",
                            ],
                        },
                        "month": {
                            "anyOf": [
                                {"type": "integer"},
                                {"type": "null"},
                            ],
                        },
                        "month_start": {
                            "anyOf": [
                                {"type": "integer"},
                                {"type": "null"},
                            ],
                        },
                        "month_end": {
                            "anyOf": [
                                {"type": "integer"},
                                {"type": "null"},
                            ],
                        },
                        "year": {
                            "anyOf": [
                                {"type": "integer"},
                                {"type": "null"},
                            ],
                        },
                    },
                    "required": [
                        "type",
                        "month",
                        "month_start",
                        "month_end",
                        "year",
                    ],
                },
                "filters": {
                    "type": "object",
                    "properties": {
                        "product": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "null"},
                            ],
                        },
                        "customer": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "null"},
                            ],
                        },
                    },
                    "required": [
                        "product",
                        "customer",
                    ],
                },
                "comparison_metric": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": sorted(ALLOWED_METRICS),
                    },
                },
                "use_business_findings": {
                    "type": "boolean",
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                },
            },
            "required": [
                "operation",
                "entity",
                "metric",
                "ranking",
                "limit",
                "time_scope",
                "filters",
                "comparison_metric",
                "use_business_findings",
                "confidence",
            ],
        }

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "automatic_function_calling": {"disable": True},
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )

        parsed = response.parsed

        if isinstance(parsed, dict):
            return parsed

    except Exception as exc:
        print(
            f"Question planner fallback: {exc}"
        )

    return None


def _merge_question_intent(
    report,
    question: str,
    plan: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Apply deterministic guardrails on top of the AI planner.

    The model may interpret ambiguous wording incorrectly. For common,
    high-confidence business questions we force the semantic intent that
    follows directly from the user's wording, while still allowing the
    model to handle richer questions.
    """
    q = (question or "").strip().lower()
    fallback = _fallback_plan(
        report,
        question,
    )
    merged = dict(
        plan
        or fallback
    )

    # Deterministic subject parsing for common customer/product wording.
    # This prevents an LLM plan from turning:
    #   "which customer bought the most products?"
    # into a product-revenue question merely because "products" is present.
    subject_match = re.search(
        r"\bwhich\s+(customer|customers|buyer|buyers|client|clients|"
        r"product|products|item|items|sku)\b",
        q,
    )
    if subject_match:
        subject = subject_match.group(1)
        if subject in {"customer", "customers", "buyer", "buyers", "client", "clients"}:
            merged["entity"] = "customer"
        else:
            merged["entity"] = "product"

    # "bought/sold the most products" means quantity unless the question
    # explicitly names another metric.
    if re.search(
        r"\b(bought|purchased|sold)\b.*\bmost\b.*\b(products?|items?|units?)\b",
        q,
    ) or re.search(
        r"\bmost\b.*\b(products?|items?|units?)\b.*\b(bought|purchased|sold)\b",
        q,
    ):
        if not any(
            phrase in q
            for phrase in (
                "revenue",
                "sales value",
                "dollar",
                "amount",
                "orders",
                "order count",
            )
        ):
            merged["metric"] = "quantity"
            merged["operation"] = "rank"

    # Do not turn vague "performed well" language into an invented KPI.
    # The UI should ask the user which measurable definition they mean.
    if re.search(
        r"\b(performed well|performing well|did well|best performance|"
        r"good performance)\b",
        q,
    ) and not any(
        phrase in q
        for phrase in (
            "revenue",
            "sales",
            "units",
            "quantity",
            "orders",
            "aov",
            "average order",
        )
    ):
        merged["_needs_clarification"] = True

    # Explicit entity words always beat an ambiguous AI entity.
    if (
        not subject_match
        and any(
            phrase in q
            for phrase in (
                "product",
                "products",
                "item",
                "items",
                "sku",
            )
        )
    ):
        merged["entity"] = "product"
    elif (
        not subject_match
        and any(
            phrase in q
            for phrase in (
                "customer",
                "customers",
                "buyer",
                "buyers",
                "client",
                "clients",
                "account",
                "accounts",
            )
        )
    ):
        merged["entity"] = "customer"

    # High-confidence ranking language.
    if merged.get("entity") in {"product", "customer"} and any(
        phrase in q
        for phrase in (
            "best",
            "top",
            "highest",
            "lowest",
            "worst",
            "most",
            "least",
            "rank",
        )
    ):
        merged["operation"] = "rank"

    # Strong metric signals.
    if any(
        phrase in q
        for phrase in (
            "units",
            "items sold",
            "quantity",
            "sold the most",
            "sold most",
        )
    ):
        merged["metric"] = "quantity"
    elif any(
        phrase in q
        for phrase in (
            "order count",
            "number of orders",
            "most orders",
            "highest orders",
        )
    ):
        merged["metric"] = "orders"
    elif any(
        phrase in q
        for phrase in (
            "average order value",
            "aov",
            "revenue per order",
            "average order",
        )
    ):
        merged["metric"] = "aov"
    elif any(
        phrase in q
        for phrase in (
            "revenue",
            "sales",
            "made the most",
            "generated the most",
        )
    ):
        merged["metric"] = "revenue"
    elif any(
        phrase in q
        for phrase in (
            "return rate",
            "refund rate",
            "returns",
        )
    ):
        merged["metric"] = "return_rate"

    # Strong comparison / explanation signals.
    if any(
        phrase in q
        for phrase in (
            "why was",
            "why did",
            "why is",
            "why were",
            "what caused",
            "cause of",
        )
    ):
        merged["operation"] = "explain_change"

    elif (
        "compare" in q
        or "compared with" in q
        or "compared to" in q
        or "difference between" in q
    ):
        merged["operation"] = "compare"

    elif "contribut" in q or "drove the decline" in q:
        merged["operation"] = "contribution"

    # Time parsing from the user's wording is authoritative when present.
    fallback_time = fallback.get(
        "time_scope",
        {"type": "period"},
    )
    if fallback_time.get("type") != "period":
        merged["time_scope"] = fallback_time
    elif not merged.get("time_scope"):
        merged["time_scope"] = fallback_time

    # Never allow the planner to invent named filters.
    filters = dict(
        merged.get(
            "filters",
            {},
        )
    )
    available_products = set(
        report.get("data", pd.DataFrame())
        .get("product", pd.Series(dtype=str))
        .dropna()
        .astype(str)
        .tolist()
    )
    available_customers = set(
        report.get("data", pd.DataFrame())
        .get("customer", pd.Series(dtype=str))
        .dropna()
        .astype(str)
        .tolist()
    )

    if filters.get("product") is not None:
        filters["product"] = (
            filters["product"]
            if str(filters["product"]) in available_products
            else None
        )

    if filters.get("customer") is not None:
        filters["customer"] = (
            filters["customer"]
            if str(filters["customer"]) in available_customers
            else None
        )

    merged["filters"] = filters

    # For a direct "best/top product/customer" question with no explicit
    # month, use the full uploaded dataset, not a stale dashboard period.
    if (
        merged.get("operation") == "rank"
        and merged.get("entity") in {"product", "customer"}
        and fallback_time.get("type") == "period"
    ):
        merged["time_scope"] = {
            "type": "period"
        }

    return merged


def plan_sales_question(report, question: str) -> dict[str, Any]:
    """
    General natural-language query planner.

    Gemini classifies the user's wording into a small, controlled intent
    schema. If Gemini is unavailable, a deterministic fallback handles
    common language patterns.
    """
    plan = _llm_plan(
        report,
        question,
    )

    if plan is None:
        plan = _fallback_plan(
            report,
            question,
        )

    return _merge_question_intent(
        report,
        question,
        plan,
    )


def _apply_filters(
    rows: pd.DataFrame,
    plan: dict[str, Any],
) -> pd.DataFrame:
    """Apply optional product/customer filters from the query plan."""
    result = rows.copy()

    filters = plan.get(
        "filters",
        {}
    ) or {}

    product = filters.get(
        "product"
    )

    customer = filters.get(
        "customer"
    )

    if product:
        matches = result[
            result["product"]
            .astype(str)
            .str.casefold()
            == str(product).casefold()
        ]

        if not matches.empty:
            result = matches

    if customer:
        matches = result[
            result["customer"]
            .astype(str)
            .str.casefold()
            == str(customer).casefold()
        ]

        if not matches.empty:
            result = matches

    return result


def _period_rows(
    rows: pd.DataFrame,
    time_scope: dict[str, Any],
    reference_month: int | None = None,
) -> pd.DataFrame:
    scope_type = time_scope.get(
        "type",
        "period",
    )

    if scope_type == "month":

        month = _month_number(
            time_scope.get("month")
        )

        if month is None:
            return rows

        year = time_scope.get(
            "year"
        ) or int(
            rows["date"].dt.year.max()
        )

        return _month_filter(
            rows,
            month,
            year,
        )

    if scope_type == "date_range":

        start = pd.to_datetime(
            time_scope.get(
                "start_date"
            ),
            errors="coerce",
        )

        end = pd.to_datetime(
            time_scope.get(
                "end_date"
            ),
            errors="coerce",
        )

        if pd.isna(start) or pd.isna(end):
            return rows

        return rows[
            (rows["date"] >= start)
            & (rows["date"] <= end)
        ].copy()

    if reference_month is not None:

        year = time_scope.get(
            "year"
        ) or int(
            rows["date"].dt.year.max()
        )

        return _month_filter(
            rows,
            reference_month,
            year,
        )

    return rows.copy()


def _group_metric(
    rows: pd.DataFrame,
    entity: str,
    metric: str,
) -> pd.Series:
    if entity == "product":

        group_col = "product"

    elif entity == "customer":

        group_col = "customer"

    else:

        raise ValueError(
            f"Unsupported ranking entity: {entity}"
        )

    if metric == "revenue":

        return rows.groupby(group_col)["revenue"].sum()

    if metric == "quantity":

        return rows.groupby(group_col)["quantity"].sum()

    if metric == "orders":

        return rows.groupby(group_col)["order_id"].nunique()

    if metric == "aov":

        revenue = rows.groupby(group_col)["revenue"].sum()
        orders = rows.groupby(group_col)["order_id"].nunique()

        return revenue / orders.replace(0, pd.NA)

    if metric == "return_rate":
        if "return_status" not in rows.columns:
            return pd.Series(dtype=float)
            
        orders = rows.groupby(group_col)["order_id"].nunique()
        returned_mask = rows["return_status"].astype(str).str.lower().str.strip().isin(['returned', 'yes', 'true', '1'])
        returned_orders = rows[returned_mask].groupby(group_col)["order_id"].nunique()
        
        return (returned_orders.reindex(orders.index, fill_value=0) / orders) * 100.0

    raise ValueError(
        f"Unsupported metric: {metric}"
    )


def _answer_rank(
    report,
    plan: dict[str, Any],
) -> str:
    rows = report["data"].copy()

    rows = _apply_filters(
        rows,
        plan,
    )

    rows = _period_rows(
        rows,
        plan.get(
            "time_scope",
            {"type": "period"},
        ),
    )

    if rows.empty:
        time_scope = plan.get(
            "time_scope",
            {},
        )

        if time_scope.get("type") == "month":
            requested_month = _month_number(
                time_scope.get("month")
            )
            requested_year = (
                time_scope.get("year")
                or _default_year(report)
            )

            data = report.get("data")
            if (
                requested_month is not None
                and data is not None
                and not data.empty
                and "date" in data.columns
            ):
                available_periods = (
                    data.assign(
                        _year=data["date"].dt.year,
                        _month=data["date"].dt.month,
                    )
                    [[" _year", "_month"]]
                    .drop_duplicates()
                    if False
                    else data.assign(
                        _year=data["date"].dt.year,
                        _month=data["date"].dt.month,
                    )[["_year", "_month"]]
                    .drop_duplicates()
                    .sort_values(["_year", "_month"])
                )

                available_labels = [
                    f"{calendar.month_name[int(row['_month'])]} {int(row['_year'])}"
                    for _, row in available_periods.iterrows()
                ]

                requested_label = (
                    f"{calendar.month_name[requested_month]} "
                    f"{requested_year}"
                )

                if available_labels:
                    return (
                        f"I couldn't answer that for {requested_label} because "
                        f"your uploaded file has no data for that month. "
                        f"Available periods in the file: "
                        + ", ".join(available_labels)
                        + "."
                    )

        return (
            "I couldn't find data matching that question within "
            "the uploaded file. Try asking about one of the periods "
            "shown in the available data."
        )

    entity = plan.get(
        "entity",
        "product",
    )

    metric = plan.get(
        "metric",
        "revenue",
    )

    values = _group_metric(
        rows,
        entity,
        metric,
    ).dropna()

    if values.empty:
        return (
            "There isn't enough data to answer that ranking question."
        )

    ascending = (
        plan.get(
            "ranking",
            "highest",
        )
        == "lowest"
    )

    top_n = int(
        plan.get(
            "limit",
            1,
        )
    )

    values = values.sort_values(
        ascending=ascending
    ).head(top_n)

    time_scope = plan.get(
        "time_scope",
        {},
    )

    scope_type = time_scope.get(
        "type",
        "period",
    )

    if scope_type == "month":
        month = _month_number(
            time_scope.get("month")
        )
        year = time_scope.get("year") or int(
            rows["date"].dt.year.max()
        )
        period_label = (
            f"{calendar.month_name[month]} {year}"
            if month
            else "the selected month"
        )
    elif scope_type == "period":
        start = rows["date"].min()
        end = rows["date"].max()
        if pd.notna(start) and pd.notna(end):
            period_label = (
                f"the full uploaded period "
                f"({start.strftime('%b %Y')}–{end.strftime('%b %Y')})"
            )
        else:
            period_label = "the full uploaded dataset"
    else:
        period_label = "the selected reporting period"

    metric_label = {
        "revenue": "revenue",
        "quantity": "units sold",
        "orders": "orders",
        "aov": "average order value",
        "return_rate": "return rate",
    }.get(
        metric,
        metric,
    )

    entity_label = (
        "product"
        if entity == "product"
        else "customer"
    )

    rank_word = "lowest" if ascending else "highest"

    if top_n == 1:

        name = values.index[0]
        value = values.iloc[0]

        return (
            f"The {entity_label} with the {rank_word} {metric_label} in "
            f"{period_label} was {name} at "
            f"{_format_metric(metric, value)}."
        )

    pieces = [
        (
            f"{idx}: {_format_metric(metric, value)}"
        )
        for idx, value in values.items()
    ]

    return (
        f"The {top_n} {entity_label}s with the {rank_word} {metric_label} in "
        f"{period_label} were: "
        + "; ".join(pieces)
        + "."
    )


def _answer_aggregate(
    report,
    plan: dict[str, Any],
) -> str:
    rows = _apply_filters(
        report["data"],
        plan,
    )

    rows = _period_rows(
        rows,
        plan.get(
            "time_scope",
            {"type": "period"},
        ),
    )

    metric = plan.get(
        "metric",
        "revenue",
    )

    value = _metric_from_rows(
        rows,
        metric,
    )

    if value is None:
        return (
            "I couldn't find enough data to calculate that."
        )

    scope = plan.get("time_scope", {})
    if scope.get("type") == "month":
        month = _month_number(scope.get("month"))
        year = scope.get("year") or _default_year(report)
        label = (
            f"{calendar.month_name[month]} {year}"
            if month else "the selected month"
        )
    else:
        label = "the full uploaded period"

    return (
        f"The {metric.replace('_', ' ')} for {label} is "
        f"{_format_metric(metric, value)}."
    )


def _comparison_month_rows(
    rows: pd.DataFrame,
    time_scope: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, str, str] | None:
    month_start = _month_number(
        time_scope.get(
            "month_start"
        )
    )

    month_end = _month_number(
        time_scope.get(
            "month_end"
        )
    )

    if month_start is None or month_end is None:
        return None

    year = time_scope.get(
        "year"
    ) or int(
        rows["date"].dt.year.max()
    )

    left = _month_filter(
        rows,
        month_start,
        year,
    )

    right = _month_filter(
        rows,
        month_end,
        year,
    )

    return (
        left,
        right,
        f"{calendar.month_name[month_start]} {year}",
        f"{calendar.month_name[month_end]} {year}",
    )


def _answer_compare(
    report,
    plan: dict[str, Any],
) -> str:
    rows = _apply_filters(
        report["data"],
        plan,
    )

    pair = _comparison_month_rows(
        rows,
        plan.get(
            "time_scope",
            {},
        ),
    )

    if pair is None:
        return (
            "Please specify two months or dates to compare."
        )

    left, right, left_label, right_label = pair

    if left.empty or right.empty:
        return (
            "I couldn't find enough sales data for both periods "
            "in the current analysis."
        )

    metrics = plan.get(
        "comparison_metric",
        [
            "revenue",
            "orders",
            "quantity",
            "aov",
        ],
    )

    pieces = []

    for metric in metrics[:4]:

        left_value = _metric_from_rows(
            left,
            metric,
        )

        right_value = _metric_from_rows(
            right,
            metric,
        )

        if (
            left_value is None
            or right_value is None
            or left_value == 0
        ):
            continue

        pct = (
            (right_value - left_value)
            / abs(left_value)
            * 100
        )

        direction = (
            "increased"
            if pct > 0
            else "decreased"
            if pct < 0
            else "was unchanged"
        )

        pieces.append(
            (
                f"{metric.upper() if metric == 'aov' else metric}: "
                f"{_format_metric(metric, left_value)} → "
                f"{_format_metric(metric, right_value)} "
                f"({direction} {abs(pct):.1f}%)"
            )
        )

    return (
        f"Compared with {left_label}, {right_label} changed as follows: "
        + " | ".join(pieces)
        + "."
    )


def _answer_explain_change(
    report,
    plan: dict[str, Any],
) -> str:
    rows = _apply_filters(
        report["data"],
        plan,
    )

    time_scope = plan.get(
        "time_scope",
        {},
    )

    # Two named months: use them directly.
    pair = _comparison_month_rows(
        rows,
        time_scope,
    )

    # One named month: compare against the immediately previous month.
    if pair is None and time_scope.get("type") == "month":

        month = _month_number(
            time_scope.get(
                "month"
            )
        )

        year = time_scope.get(
            "year"
        ) or int(
            rows["date"].dt.year.max()
        )

        if month is not None:

            current = _month_filter(
                rows,
                month,
                year,
            )

            previous_month = (
                month - 1
                if month > 1
                else 12
            )

            previous_year = (
                year
                if month > 1
                else year - 1
            )

            previous = _month_filter(
                rows,
                previous_month,
                previous_year,
            )

            pair = (
                previous,
                current,
                f"{calendar.month_name[previous_month]} {previous_year}",
                f"{calendar.month_name[month]} {year}",
            )

    # No explicit period: use the highest-priority deterministic finding
    # when the question asks for the cause of a weakness/decline.
    if pair is None:

        findings = report.get(
            "business_findings",
            {},
        ).get(
            "priority_findings",
            [],
        )

        decline = next(
            (
                finding
                for finding in findings
                if finding.get("type") == "revenue_drop"
            ),
            None,
        )

        if decline:

            response = (
                f"{decline.get('message', '')} "
                f"The primary measurable driver was "
                f"{decline.get('primary_driver', 'not isolated')}."
            )

            if decline.get("driver_product_text"):
                response += (
                    f" Product-level contributors were "
                    f"{decline['driver_product_text']}."
                )

            response += (
                " The sales data identifies the measurable pattern, "
                "but does not establish the operational cause."
            )

            return response

        return (
            "I need a month or comparison period to explain a specific "
            "change."
        )

    left, right, left_label, right_label = pair

    if left.empty or right.empty:
        return (
            f"I don't have enough data to compare {left_label} and "
            f"{right_label}."
        )

    revenue_left = _metric_from_rows(
        left,
        "revenue",
    )

    revenue_right = _metric_from_rows(
        right,
        "revenue",
    )

    orders_left = _metric_from_rows(
        left,
        "orders",
    )

    orders_right = _metric_from_rows(
        right,
        "orders",
    )

    aov_left = _metric_from_rows(
        left,
        "aov",
    )

    aov_right = _metric_from_rows(
        right,
        "aov",
    )

    quantity_left = _metric_from_rows(
        left,
        "quantity",
    )

    quantity_right = _metric_from_rows(
        right,
        "quantity",
    )

    if not revenue_left or revenue_right is None:
        return (
            "I couldn't calculate the revenue change for those periods."
        )

    revenue_pct = (
        (revenue_right - revenue_left)
        / abs(revenue_left)
        * 100
    )

    orders_pct = (
        (
            (orders_right - orders_left)
            / abs(orders_left)
            * 100
        )
        if orders_left
        else None
    )

    aov_pct = (
        (
            (aov_right - aov_left)
            / abs(aov_left)
            * 100
        )
        if aov_left
        else None
    )

    quantity_pct = (
        (
            (quantity_right - quantity_left)
            / abs(quantity_left)
            * 100
        )
        if quantity_left
        else None
    )

    driver = "revenue movement"

    if (
        revenue_pct < 0
        and orders_pct is not None
        and aov_pct is not None
    ):
        if abs(orders_pct) > abs(aov_pct):
            driver = "order volume"
        else:
            driver = "average order value"

    elif (
        revenue_pct > 0
        and orders_pct is not None
        and aov_pct is not None
    ):
        if abs(aov_pct) >= abs(orders_pct):
            driver = "average order value"
        else:
            driver = "order volume"

    response = (
        f"Revenue changed from "
        f"{_format_metric('revenue', revenue_left)} in {left_label} "
        f"to {_format_metric('revenue', revenue_right)} in {right_label} "
        f"({revenue_pct:+.1f}%). "
        f"The strongest measurable driver was {driver}."
    )

    response += (
        f" Orders changed from {orders_left:,.0f} to "
        f"{orders_right:,.0f} ({orders_pct:+.1f}%)."
        if orders_pct is not None
        else ""
    )

    response += (
        f" AOV changed from ${aov_left:,.2f} to "
        f"${aov_right:,.2f} ({aov_pct:+.1f}%)."
        if aov_pct is not None
        else ""
    )

    response += (
        f" Items changed from {quantity_left:,.0f} to "
        f"{quantity_right:,.0f} ({quantity_pct:+.1f}%)."
        if quantity_pct is not None
        else ""
    )

    # Deterministic product contribution for the same periods.
    if (
        not left.empty
        and not right.empty
        and "product" in left.columns
    ):
        product_left = (
            left.groupby("product")["revenue"]
            .sum()
        )

        product_right = (
            right.groupby("product")["revenue"]
            .sum()
        )

        delta = (
            product_right
            .sub(product_left, fill_value=0)
            .sort_values()
        )

        if revenue_pct < 0 and not delta.empty:

            drags = delta.head(3)

            response += (
                " Largest product revenue declines were "
                + "; ".join(
                    f"{name} {_format_metric('revenue', abs(value))}"
                    for name, value in drags.items()
                    if value < 0
                )
                + "."
            )

    response += (
        " The sales data identifies the measurable pattern, "
        "but does not establish the operational cause."
    )

    return response


def _answer_contribution(
    report,
    plan: dict[str, Any],
) -> str:
    rows = _apply_filters(
        report["data"],
        plan,
    )

    time_scope = plan.get(
        "time_scope",
        {},
    )

    pair = _comparison_month_rows(
        rows,
        time_scope,
    )

    if pair is None:

        findings = report.get(
            "business_findings",
            {},
        ).get(
            "priority_findings",
            [],
        )

        finding = next(
            (
                f for f in findings
                if f.get("type") == "revenue_drop"
            ),
            None,
        )

        if finding and finding.get(
            "driver_product_text"
        ):

            return (
                f"The products associated with the largest measurable "
                f"change were {finding['driver_product_text']}."
            )

        return (
            "Please specify the periods when you want the product "
            "contribution compared."
        )

    left, right, left_label, right_label = pair

    if left.empty or right.empty:
        return (
            f"I don't have enough data to compare {left_label} and "
            f"{right_label}."
        )

    revenue_left = (
        left.groupby("product")["revenue"]
        .sum()
    )

    revenue_right = (
        right.groupby("product")["revenue"]
        .sum()
    )

    delta = (
        revenue_right
        .sub(
            revenue_left,
            fill_value=0
        )
        .sort_values()
    )

    if delta.empty:
        return (
            "There isn't enough product-level data for that comparison."
        )

    rows_out = []

    for product, value in delta.head(5).items():

        if value < 0:

            rows_out.append(
                f"{product}: {_format_metric('revenue', abs(value))} decline"
            )

    for product, value in delta.sort_values(
        ascending=False
    ).head(5).items():

        if value > 0:

            rows_out.append(
                f"{product}: {_format_metric('revenue', value)} increase"
            )

    return (
        f"From {left_label} to {right_label}, the main product-level "
        f"revenue movements were: "
        + "; ".join(rows_out)
        + "."
    )


def execute_sales_plan(
    report,
    plan: dict[str, Any],
) -> str:
    """Execute an already-validated query plan without replanning."""
    metric = plan.get("metric", "")
    if metric == "return_rate":
        rows = report.get("data")
        if rows is None or "return_status" not in rows.columns:
            return "Product return rate cannot be calculated from the uploaded file."
            
    operation = plan.get("operation", "lookup")

    try:
        if operation == "rank":
            return _answer_rank(report, plan)
        if operation == "aggregate":
            return _answer_aggregate(report, plan)
        if operation == "compare":
            return _answer_compare(report, plan)
        if operation == "explain_change":
            return _answer_explain_change(report, plan)
        if operation == "trend":
            return (
                "The trend is shown in the Performance section. "
                "Ask for a specific metric and period if you need a direct calculation."
            )
        if operation == "contribution":
            return _answer_contribution(report, plan)

        return (
            "I understand the question, but I don't have a verified query "
            "for that wording yet. Try asking for a specific metric, ranking, "
            "comparison, or reason for a change rather than receiving a guessed KPI."
        )
    except Exception as exc:
        print(f"Sales query execution failed: {exc}")
        return (
            "I couldn't answer that question from the available sales data. "
            "Try asking about revenue, orders, units sold, average order value, "
            "products, customers, or specific months."
        )


def answer_sales_question(
    report,
    question: str,
) -> str:
    """Plan once, then execute the exact same verified plan."""
    question = (question or "").strip()
    if not question:
        return "Please enter a question about your business."

    plan = plan_sales_question(report, question)
    return execute_sales_plan(report, plan)


def answer_sales_question_structured(
    report,
    question: str,
) -> dict[str, Any]:
    """Return the answer plus the exact plan used, for transparent UI evidence."""
    question = (question or "").strip()
    if not question:
        return {
            "answer": "Please enter a question about your business.",
            "plan": {},
        }

    plan = plan_sales_question(report, question)
    return {
        "answer": execute_sales_plan(report, plan),
        "plan": plan,
    }
