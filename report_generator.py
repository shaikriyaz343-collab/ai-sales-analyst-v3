import os
import re
import calendar
import io
from pathlib import Path
from google import genai
import pandas as pd

from sales_query_engine_v1 import (
    answer_sales_question as _general_answer_sales_question,
)

def normalize_column_name(column):
    """
    Convert a column name into a standard comparable format.
    """

    text = str(column).strip()

    # Convert common camel-case headers such as OrderID -> Order ID
    # and CustomerName -> Customer Name before normalizing.
    text = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])",
        " ",
        text,
    )

    text = re.sub(
        r"(?<=[A-Z])(?=[A-Z][a-z])",
        " ",
        text,
    )

    return (
        text
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )
def map_columns(df):
    """
    Map common business/sales column names to the report's standard names.

    Extra columns such as Region, Payment Method, Order Status, SKU, etc.
    are intentionally allowed and ignored unless used by a future feature.
    """

    column_aliases = {
        "date": [
            "date",
            "order date",
            "orderdate",
            "sale date",
            "sales date",
            "transaction date",
            "transactiondate",
        ],

        "order_id": [
            "order id",
            "orderid",
            "order number",
            "order no",
            "invoice",
            "invoice number",
            "invoice no",
            "invoice #",
            "transaction id",
            "transactionid",
        ],

        "customer": [
            "customer",
            "customer name",
            "customername",
            "client",
            "client name",
            "buyer",
        ],

        "product": [
            "product",
            "product name",
            "productname",
            "item",
            "item name",
            "service",
            "service name",
        ],

        "category": [
            "category",
            "product category",
            "productcategory",
            "item category",
            "type",
        ],

        "quantity": [
            "quantity",
            "qty",
            "units",
            "units sold",
            "quantity sold",
            "items sold",
        ],

        "price": [
            "price",
            "unit price",
            "unitprice",
            "selling price",
            "sale price",
            "item price",
        ],

        "revenue": [
            "revenue",
            "sales",
            "sales amount",
            "total amount",
            "totalamount",
            "amount",
            "order total",
            "order total amount",
            "net sales",
        ],
    }

    normalized_columns = {
        normalize_column_name(column): column
        for column in df.columns
    }

    rename_map = {}

    for standard_name, aliases in column_aliases.items():

        for alias in aliases:

            normalized_alias = normalize_column_name(alias)

            if normalized_alias in normalized_columns:

                original_column = normalized_columns[
                    normalized_alias
                ]

                rename_map[
                    original_column
                ] = standard_name

                break

    return df.rename(
        columns=rename_map
    )



def _unwrap_single_column_csv(df, file_path):
    """
    Handle CSV files that have been exported/wrapped as one quoted column.

    Example:
        fld1
        "OrderID,OrderDate,CustomerName,..."
        "1001,2026-01-05,James Wilson,..."

    This is common when data has passed through another reporting/export
    system. We recover the embedded CSV rather than rejecting the file.
    """

    if df.shape[1] != 1:
        return df

    raw_column = str(
        df.columns[0]
    ).strip()

    values = df.iloc[:, 0].astype(str)

    # Normal one-column files can legitimately exist. Only unwrap when
    # there is strong evidence that each row contains comma-separated data.
    comma_row_ratio = (
        values.str.contains(
            ",",
            regex=False
        ).mean()
    )

    looks_like_wrapper = (
        comma_row_ratio >= 0.8
        and (
            raw_column.lower() in {
                "fld1",
                "column1",
                "unnamed: 0",
            }
            or values.iloc[0].count(",") >= 3
        )
    )

    if not looks_like_wrapper:
        return df

    raw_lines = Path(file_path).read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines()

    # The wrapper's first line (for example "fld1") is not part of the
    # embedded CSV. Drop it before parsing the inner header.
    if raw_lines and raw_lines[0].strip().lower() == raw_column.lower():
        raw_lines = raw_lines[1:]

    # Strip the outer CSV quoting from each line, then parse the inner CSV.
    inner_lines = []

    for line in raw_lines:

        stripped = line.strip()

        if (
            len(stripped) >= 2
            and stripped.startswith('"')
            and stripped.endswith('"')
        ):
            stripped = stripped[1:-1].replace(
                '""',
                '"',
            )

        inner_lines.append(
            stripped
        )

    inner_text = "\n".join(
        inner_lines
    )

    parsed = pd.read_csv(
        io.StringIO(
            inner_text
        )
    )

    return parsed


def load_sales_data(file_path):

    file_path_lower = file_path.lower()

    if file_path_lower.endswith(".csv"):

        df = pd.read_csv(
            file_path
        )

        df = _unwrap_single_column_csv(
            df,
            file_path,
        )

    elif file_path_lower.endswith(".xlsx"):

        df = pd.read_excel(
            file_path
        )

    else:

        raise ValueError(
            "Only CSV and Excel files are supported."
        )

    return df



def validate_columns(df):

    required_columns = [
        "date",
        "order_id",
        "customer",
        "product",
        "quantity",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if (
        "price" not in df.columns
        and "revenue" not in df.columns
    ):
        missing_columns.append(
            "price_or_revenue"
        )

    if missing_columns:

        friendly_names = {
            "date": "Date / Order Date",
            "order_id": "Order ID / Invoice Number",
            "customer": "Customer / Client",
            "product": "Product / Item",
            "category": "Category",
            "quantity": "Quantity / Qty",
            "price": "Price / Unit Price",
            "revenue": "Revenue / Total Amount",
            "price_or_revenue": (
                "Price / Unit Price OR Revenue / Total Amount"
            ),
        }

        message = (
            "\n\n"
            "❌ We could not process this file.\n\n"
            "Missing required business fields:\n"
        )

        for column in missing_columns:

            message += (
                f"   • {friendly_names[column]}\n"
            )

        message += (
            "\nWe can handle many different column names and extra fields. "
            "We need date, order, customer, product, quantity, and either "
            "unit price or a total revenue/amount field."
        )

        raise ValueError(
            message
        )



def validate_data_values(df):

    errors = []

        # -------------------------
    # Validate empty dataset
    # -------------------------

    if df.empty:
        raise ValueError(
            "\n\n"
            "❌ We could not process this file.\n\n"
            "The uploaded file contains no sales records.\n\n"
            "Please upload a file containing at least one "
            "sales transaction and try again."
        )
    
    # -------------------------
    # Validate dates
    # -------------------------

    invalid_dates = pd.to_datetime(
        df["date"],
        errors="coerce"
    ).isna()

    if invalid_dates.any():
        errors.append(
            f"Invalid dates found: "
            f"{invalid_dates.sum()} row(s)"
        )


    # -------------------------
    # Validate quantity
    # -------------------------

    quantity_numeric = pd.to_numeric(
        df["quantity"],
        errors="coerce"
    )

    invalid_quantity = (
        quantity_numeric.isna()
        | (quantity_numeric <= 0)
    )

    if invalid_quantity.any():
        errors.append(
            f"Invalid quantity values found: "
            f"{invalid_quantity.sum()} row(s). "
            f"Quantity must be greater than 0."
        )


    # -------------------------
    # Validate price / revenue
    # -------------------------

    if "price" in df.columns:

        price_numeric = pd.to_numeric(
            df["price"],
            errors="coerce"
        )

        invalid_price = (
            price_numeric.isna()
            | (price_numeric <= 0)
        )

        if invalid_price.any():
            errors.append(
                f"Invalid price values found: "
                f"{invalid_price.sum()} row(s). "
                f"Price must be greater than 0."
            )

    elif "revenue" in df.columns:

        revenue_numeric = pd.to_numeric(
            df["revenue"],
            errors="coerce"
        )

        invalid_revenue = (
            revenue_numeric.isna()
            | (revenue_numeric <= 0)
        )

        if invalid_revenue.any():
            errors.append(
                f"Invalid revenue values found: "
                f"{invalid_revenue.sum()} row(s). "
                f"Revenue must be greater than 0."
            )


    # -------------------------
    # Show ALL errors
    # -------------------------

    if errors:

        message = (
            "\n\n"
            "❌ We could not process this file.\n\n"
            "Data problems found:\n\n"
        )

        for error in errors:
            message += (
                f"\n• {error}\n"
            )

        message += (
            "\nPlease correct the data and try again."
        )

        raise ValueError(message)

def prepare_data(df):

    df = df.copy()

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df["quantity"] = pd.to_numeric(
        df["quantity"]
    )

    if "category" not in df.columns:
        df["category"] = "Uncategorized"

    if "revenue" in df.columns:

        df["revenue"] = pd.to_numeric(
            df["revenue"],
            errors="coerce",
        )

    if "price" in df.columns:

        df["price"] = pd.to_numeric(
            df["price"],
            errors="coerce",
        )

    # Prefer the supplied revenue/total amount when present.
    if (
        "revenue" in df.columns
        and df["revenue"].notna().any()
    ):

        if "price" not in df.columns:
            df["price"] = (
                df["revenue"]
                / df["quantity"]
            )

        else:

            missing_revenue = df["revenue"].isna()

            df.loc[
                missing_revenue,
                "revenue"
            ] = (
                df.loc[
                    missing_revenue,
                    "quantity"
                ]
                * df.loc[
                    missing_revenue,
                    "price"
                ]
            )

    else:

        df["revenue"] = (
            df["quantity"]
            * df["price"]
        )

    return df



def calculate_kpis(df):

    total_revenue = df["revenue"].sum()

    total_orders = df["order_id"].nunique()

    total_quantity = df["quantity"].sum()

    average_order_value = round(
    (total_revenue / total_orders) + 1e-9,
    2
    )

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_quantity": total_quantity,
        "average_order_value": average_order_value
    }


def analyze_products(df):

    product_analysis = (
        df.groupby("product")
        .agg(
            orders=("order_id", "nunique"),
            quantity_sold=("quantity", "sum"),
            revenue=("revenue", "sum")
        )
        .sort_values("revenue", ascending=False)
    )

    total_revenue = product_analysis["revenue"].sum()

    product_analysis["revenue_percentage"] = (
        product_analysis["revenue"]
        / total_revenue
        * 100
    )

    product_analysis["revenue_per_order"] = (
        product_analysis["revenue"]
        / product_analysis["orders"]
    )

    return product_analysis


def analyze_customers(df):

    customer_analysis = (
        df.groupby("customer")
        .agg(
            orders=("order_id", "nunique"),
            quantity_purchased=("quantity", "sum"),
            revenue=("revenue", "sum")
        )
        .sort_values("revenue", ascending=False)
    )

    total_revenue = customer_analysis["revenue"].sum()

    customer_analysis["revenue_percentage"] = (
        customer_analysis["revenue"]
        / total_revenue
        * 100
    )

    customer_analysis["revenue_per_order"] = (
        customer_analysis["revenue"]
        / customer_analysis["orders"]
    )

    return customer_analysis


def analyze_monthly_sales(df):

    monthly_sales = (
        df.groupby(df["date"].dt.to_period("M"))
        .agg(
            revenue=("revenue", "sum"),
            orders=("order_id", "nunique"),
            quantity=("quantity", "sum")
        )
    )

    return monthly_sales

from business_intelligence import (
    build_business_findings
)

def generate_ai_prompt(report):

    kpis = report["kpis"]
    products = report["products"]
    customers = report["customers"]
    monthly = report["monthly"]
    reporting_period = report["reporting_period"]
    business_intelligence = report.get(
        "business_findings",
        {}
    )

    priority_findings = business_intelligence.get(
        "priority_findings",
        []
    )

    positive_findings = business_intelligence.get(
        "positive_findings",
        []
    )

    findings_for_ai = (
        priority_findings
        + positive_findings
    )

    findings_text = "\n".join(
        [
            (
                f"- [{finding.get('severity', 'low').upper()}] "
                f"{finding.get('message', '')} "
                f"(priority score: "
                f"{finding.get('priority_score', 0)})\n"
                f"  What happened: "
                f"{finding.get('what_happened', '')}\n"
                f"  Why it matters: "
                f"{finding.get('why_it_matters', '')}\n"
                f"  Investigate next: "
                f"{finding.get('investigate_next', '')}\n"
                f"  Primary measurable driver: "
                f"{finding.get('primary_driver', '')}\n"
                f"  Product-level revenue contribution: "
                f"{finding.get('product_contribution_text', '')}\n"
                f"  Product/metric context: "
                f"{finding.get('driver_product_text', '')}"
            )
            for finding in findings_for_ai
        ]
    )

    if not findings_text:
        findings_text = (
            "- No deterministic business findings were triggered."
        )

    prompt = f"""
You are an AI sales analyst helping a small business owner.

Turn the verified sales metrics and deterministic business findings
below into a concise management-level analysis.

The goal is not to repeat the dashboard.

The executive analysis MUST synthesize the deterministic business findings
into a management-level story.

The dashboard's Key Insights and Recommendations are grounded in
deterministic Python evidence. Use your model reasoning primarily to
improve the Executive Summary and the detailed Product, Customer, and
Monthly analysis.

Use the Business Signals as evidence, but do NOT copy their wording.
Combine related facts into a concise explanation of what changed and why
the pattern matters.

The KPI totals are supporting context, not the main story.

The analysis should answer:
- What is the single most important business change?
- Which measurable metric best explains it?
- Which products contributed to that measurable change, when available?
- What changed in the strongest positive period?
- What should the owner investigate next?
- What is a reasonable action to test, without claiming the cause is proven?

Do not write a list of signals disguised as an executive summary.
Analyze the verified sales metrics below.

IMPORTANT:
Use only the metrics provided in this prompt as factual evidence.
Do not invent causes or business conditions that are not present in
the data. Clearly distinguish between:
1. What the data shows
2. What should be investigated
3. What could be tested as an action

BUSINESS KPIs
-------------
Total Revenue: ${kpis["total_revenue"]:,.2f}
Total Orders: {kpis["total_orders"]:,}
Total Items Sold: {kpis["total_quantity"]:,}
Average Order Value: ${kpis["average_order_value"]:,.2f}

REPORTING PERIOD
----------------
Start Date: {reporting_period["start"].strftime("%B %d, %Y")}
End Date: {reporting_period["end"].strftime("%B %d, %Y")}


PRODUCT PERFORMANCE
-------------------
{products.round(2).to_string()}


CUSTOMER PERFORMANCE
--------------------
{customers.round(2).to_string()}


MONTHLY PERFORMANCE
-------------------
{monthly.round(2).to_string()}


PRIORITIZED DETERMINISTIC BUSINESS FINDINGS
----------------------------------------------
These findings were calculated by Python rules and ranked by
transparent priority scores.

Treat them as verified observations.
Do not invent causes.
Focus the executive summary and recommendations primarily
on the highest-priority findings.

{findings_text}


TASK
----
Return the analysis using exactly these sections.

EXECUTIVE SUMMARY
- Write 2-4 sentences as a connected narrative, not a list.
- Start with the most important business change.
- Explain the measurable driver using the metric breakdown.
- Mention the most important product contribution when available.
- Contrast the main weakness with the strongest positive movement when useful.
- End with the most important thing the owner should investigate or test.
- Include at least one concrete implication for the owner.
- Do NOT start with "The business generated..." and do not lead with KPI totals.
- Do NOT repeat the exact wording of any Business Signal card.

KEY INSIGHTS
- Insight 1 MUST explain the highest-priority negative development and why it matters.
- Insight 2 MUST connect the revenue movement to the strongest measurable driver.
- Insight 3 SHOULD explain which products contributed to that driver when available.
- Insight 4 SHOULD explain what was different about the strongest positive movement
  and what could be learned from it.
- Insight 5 may identify a second-order customer, product, or monthly pattern.
- Each insight should add interpretation or comparison; do not simply restate a Business Signal.
- Do NOT use KPI-only statements such as "Total revenue was..." unless
  the number is directly relevant to a finding.

PRODUCT INSIGHTS
- Observation 1
- Observation 2
- Observation 3

CUSTOMER INSIGHTS
- Observation 1
- Observation 2

MONTHLY INSIGHTS
- Observation 1
- Observation 2
- Observation 3

RECOMMENDATIONS
---------------
Provide exactly 3 practical recommendations based only on the verified sales data.

Each recommendation must have this structure:
1. Action: what the owner should do.
2. Evidence: the specific metric, period, or product that supports the action.
3. Purpose: what the owner is trying to learn, validate, or test.

Recommendations must be more useful than "investigate X".
Use concrete actions such as:
- compare a weak period with a strong period,
- identify which products account for a measurable decline,
- review product mix or revenue-per-order patterns,
- test a targeted product bundle or upsell,
- review a specific customer's contribution over time.

Do not claim that an action will definitely improve revenue.
Use "test", "evaluate", "compare", or "consider" where the outcome is uncertain.

Rules:
- For each major finding, structure the reasoning as:
  1. What happened
  2. Metric breakdown
  3. Primary measurable driver, when available
  4. Product-level contribution, when available
  5. Why it matters
  6. What to investigate next
- When product-level contribution evidence is available, distinguish:
  * product-level revenue contribution, and
  * products driving the primary measurable metric when that metric is
    directly decomposable from the available data (for example, orders).
- When the primary driver is AOV, describe product-level figures as
  "product-level revenue movement during the period" unless a true
  within-product AOV decomposition is available.
- Do not present product movement as proof of the operational cause.
- Treat the deterministic Python findings as factual evidence.
- Do not simply restate the Business Signals cards. Add useful synthesis.
- The AI Analyst must explain the relationship between the top finding,
  the measurable driver, product contribution, and business implication.
- Combine related metrics into one coherent explanation instead of listing
  them separately.
- Avoid generic recommendations such as "monitor trends regularly"
  unless they are tied to a specific finding, metric, product, or period.
- When a high-priority negative finding and a positive finding coexist,
  explain the contrast when it helps the owner understand the business.
- Do not claim that pricing, costs, margins, promotions, inventory,
  marketing, or operational problems exist unless the data directly
  demonstrates them.
- If the data suggests something worth investigating, describe it as
  something to investigate or test.
- Prefer measurable actions such as testing bundles, upsells,
  customer engagement, or investigating differences between strong
  and weak months.
- Include the relevant metric or number when possible.
- Do not present assumptions as facts.

IMPORTANT WORDING RULES
-----------------------
- Use "revenue" or "revenue per order", not "profit", "margin",
  "financial return", or similar terms unless those metrics are
  explicitly provided.
- Do not claim that pricing is a problem because a product has
  lower revenue per order. Instead, say that the relationship
  between pricing, volume, and revenue could be investigated.
- Do not claim that seasonality or operational issues caused a
  monthly revenue change unless the data directly proves the cause.
- When a cause cannot be established from the data, use wording
  such as "investigate", "explore", or "test".

MONTHLY INSIGHT RULE
--------------------
Describe monthly performance using the verified revenue, order,
and quantity metrics.

Do not describe a change as "seasonal", "operational", or caused
by a particular factor unless that factor is present in the data.

PRODUCT INSIGHT RULE
--------------------
Use "revenue per order" when discussing order economics.

Do not describe revenue per order as profit, margin, or financial
return.

If a product has high volume but lower revenue per order, describe
this as an opportunity to investigate or test bundles, upsells,
product mix, or other sales strategies.

ADDITIONAL ANALYSIS RULES

1. Python-calculated metrics are authoritative.
   Do not recalculate totals, percentages, averages, or rankings.

2. Use the exact numbers provided in the report.

3. Round monetary values to two decimal places.

4. Do not claim causation unless the data explicitly supports it.
   For example, do not say sales increased because customers preferred
   a product unless customer preference data is provided.

5. Distinguish:
   - FACT: directly supported by the data.
   - INFERENCE: a reasonable interpretation of the data.
   - RECOMMENDATION: an action worth testing.

6. Do not recommend inventory changes unless inventory data is provided.

7. Do not claim profitability, margin, ROI, customer satisfaction,
   customer preference, or demand unless those metrics are provided.

8. Recommendations must be connected to at least one specific metric.

9. Use words such as "consider", "investigate", "test", or "evaluate"
   when the recommendation has not been directly proven by the data.

10. Do not simply repeat the tables.
    Explain why the observation could matter to a small business owner.

11. When comparing products, customers, or months, explain the
    business significance of the comparison.

12. Never invent missing information.
13. Never mention cash flow, profit, margin, ROI, customer preference,
    demand, inventory, ticket size, "higher-ticket items", or similar
    concepts unless the corresponding metric is explicitly present in
    the verified report context.
14. Do not convert a revenue or AOV change into a causal statement about
    products unless the deterministic findings explicitly establish the
    measurable relationship.
15. When evidence is insufficient, say "the available sales data does not
    establish the cause" or equivalent wording.
"""

    return prompt


def generate_report(file_path):

    df = load_sales_data(file_path)

    df = map_columns(df)

    validate_columns(df)

    validate_data_values(df)

    df = prepare_data(df)

    reporting_period = {
    "start": df["date"].min(),
    "end": df["date"].max()
    }


    kpis = calculate_kpis(df)

    product_analysis = analyze_products(df)

    customer_analysis = analyze_customers(df)

    monthly_analysis = analyze_monthly_sales(df)

    report = {
        "data": df,
        "kpis": kpis,
        "products": product_analysis,
        "customers": customer_analysis,
        "monthly": monthly_analysis,
        "reporting_period": reporting_period
    }

    report["business_findings"] = build_business_findings(
        report
    )

    return report


def _build_key_insights_from_findings(report):
    """
    Create concise, evidence-based key insights from deterministic findings.
    This prevents the AI Analyst from simply echoing the full Business Signals.
    """
    business_findings = report.get(
        "business_findings",
        {}
    )

    priority_findings = business_findings.get(
        "priority_findings",
        []
    )

    positive_findings = business_findings.get(
        "positive_findings",
        []
    )

    insights = []

    for finding in priority_findings[:3]:

        message = finding.get(
            "message",
            "Priority business change detected."
        )

        driver = finding.get(
            "primary_driver"
        )

        insight = message

        if driver:
            insight += (
                f" The measurable driver was {driver}."
            )

        product_driver = finding.get(
            "driver_product_text",
            ""
        )

        if product_driver and driver == "order volume":
            insight += (
                f" The largest product-level order changes were "
                f"{product_driver}."
            )

        elif product_driver and driver == "average order value":
            insight += (
                f" The related product-level revenue movement was "
                f"{product_driver}."
            )

        insights.append(insight)

    if positive_findings:

        strongest = positive_findings[0]

        positive_insight = (
            f"{strongest.get('message', 'Positive movement was observed.')} "
        )

        if strongest.get("primary_driver"):
            positive_insight += (
                f"The measurable driver was "
                f"{strongest['primary_driver']}, "
            )

        positive_insight += (
            "which is worth comparing with the weaker periods "
            "to identify a repeatable pattern."
        )

        insights.append(
            positive_insight
        )

    # Add one non-signal business context insight only when needed.
    products = report.get("products")

    if products is not None and not products.empty:

        top_product = products.index[0]
        top_revenue = float(
            products.iloc[0]["revenue"]
        )

        insights.append(
            f"{top_product} generated "
            f"${top_revenue:,.2f}, making it the largest "
            f"revenue contributor in the selected period."
        )

    return insights[:5]


def _build_actionable_recommendations(report):
    """
    Create recommendations using Action + Evidence + Purpose.
    These are deterministic so the dashboard cannot fall back to
    generic 'investigate X' wording.
    """
    business_findings = report.get(
        "business_findings",
        {}
    )

    priority_findings = business_findings.get(
        "priority_findings",
        []
    )

    positive_findings = business_findings.get(
        "positive_findings",
        []
    )

    recommendations = []

    for finding in priority_findings[:2]:

        message = finding.get(
            "message",
            ""
        )

        driver = finding.get(
            "primary_driver",
            ""
        )

        period = finding.get(
            "period",
            ""
        )

        previous_period = finding.get(
            "previous_period",
            ""
        )

        driver_product_text = finding.get(
            "driver_product_text",
            ""
        )

        change_pct = finding.get(
            "change_pct"
        )

        # Some findings (for example product concentration) are not
        # month-over-month findings and therefore have no change_pct.
        # Handle those separately instead of formatting None as a float.
        if (
            finding.get("type") == "product_concentration"
            or change_pct is None
        ):

            product_name = finding.get(
                "product",
                "the leading product"
            )

            revenue = finding.get(
                "revenue"
            )

            revenue_share = finding.get(
                "revenue_share_pct"
            )

            if revenue is not None and revenue_share is not None:

                evidence = (
                    f"{product_name} generated "
                    f"${float(revenue):,.2f}, representing "
                    f"{float(revenue_share):.2f}% of total revenue"
                )

            else:

                evidence = (
                    finding.get(
                        "what_happened",
                        message
                    )
                )

            recommendations.append(
                f"**Action:** Review the monthly sales trend and order volume "
                f"for {product_name}. **Evidence:** {evidence}. "
                f"**Purpose:** determine whether the concentration is stable "
                f"or changing before deciding whether product-mix or "
                f"cross-sell actions should be tested."
            )

            continue

        # Recommendation for order-volume driven declines.
        if driver == "order volume":

            evidence = (
                f"orders changed from "
                f"{finding.get('previous_orders', 0):,} to "
                f"{finding.get('current_orders', 0):,} "
                f"({finding.get('order_change_pct', 0):+.1f}%)"
            )

            action = (
                f"Compare {previous_period} with {period} "
                f"order activity for the products contributing "
                f"the largest order decline"
            )

            if driver_product_text:
                evidence += (
                    f"; product-level order changes were "
                    f"{driver_product_text}"
                )

            purpose = (
                "to determine where the transaction decline was "
                "concentrated before deciding what sales action to test"
            )

        # Recommendation for AOV-driven movements.
        elif driver == "average order value":

            evidence = (
                f"AOV changed from "
                f"${finding.get('previous_aov', 0):,.2f} to "
                f"${finding.get('current_aov', 0):,.2f} "
                f"({finding.get('aov_change_pct', 0):+.1f}%)"
            )

            action = (
                f"Compare product mix and per-order purchasing patterns "
                f"between {previous_period} and {period}"
            )

            purpose = (
                "to understand which measurable mix changes are associated "
                "with the lower or higher revenue per order"
            )

        # Recommendation for mixed drivers.
        else:

            numeric_change_pct = float(change_pct)

            evidence = (
                f"revenue changed by {numeric_change_pct:+.1f}% "
                f"from {previous_period} to {period}"
            )

            action = (
                f"Compare orders, items, AOV, and product mix between "
                f"{previous_period} and {period}"
            )

            purpose = (
                "to identify which measurable component contributed most "
                "to the revenue movement"
            )

        recommendations.append(
            f"**Action:** {action}. "
            f"**Evidence:** {evidence}. "
            f"**Purpose:** {purpose}."
        )

    # Add a positive-pattern recommendation.
    if positive_findings and len(recommendations) < 3:

        finding = positive_findings[0]

        recommendations.append(
            f"**Action:** Compare the strongest positive period "
            f"({finding.get('previous_period', '')} → "
            f"{finding.get('period', '')}) with the weaker periods. "
            f"**Evidence:** {finding.get('message', '')} "
            f"The measurable driver was "
            f"{finding.get('primary_driver', 'the observed revenue movement')}. "
            f"**Purpose:** identify a repeatable product or order pattern "
            f"that could be evaluated in a future sales test."
        )

    # Fallback third recommendation if needed.
    if len(recommendations) < 3:

        products = report.get("products")

        if products is not None and not products.empty:

            top_product = products.index[0]
            top_revenue = float(
                products.iloc[0]["revenue"]
            )

            recommendations.append(
                f"**Action:** Compare {top_product} with lower-revenue products "
                f"to evaluate a product-mix or upsell test. "
                f"**Evidence:** {top_product} generated "
                f"${top_revenue:,.2f}, the highest product revenue. "
                f"**Purpose:** identify whether its sales pattern suggests "
                f"a testable product-mix opportunity."
            )

    return recommendations[:3]



def _build_grounded_executive_summary(report):
    """
    Build the Executive Summary from deterministic findings only.

    This prevents the most visible management narrative from introducing
    unsupported causal claims while still allowing the AI to provide
    detailed interpretation elsewhere in the report.
    """
    business_findings = report.get(
        "business_findings",
        {}
    )

    priority_findings = business_findings.get(
        "priority_findings",
        []
    )

    positive_findings = business_findings.get(
        "positive_findings",
        []
    )

    if not priority_findings:

        kpis = report["kpis"]

        return (
            f"The selected reporting period generated "
            f"${kpis['total_revenue']:,.2f} across "
            f"{kpis['total_orders']:,} orders with an average "
            f"order value of ${kpis['average_order_value']:,.2f}. "
            "No material negative business signal was triggered."
        )

    top = priority_findings[0]

    summary = (
        f"{top.get('message', 'A material revenue change was detected.')} "
    )

    driver = top.get(
        "primary_driver"
    )

    if driver:

        summary += (
            f"The primary measurable driver was {driver}. "
        )

    product_text = top.get(
        "driver_product_text",
        ""
    )

    if product_text and driver == "order volume":

        summary += (
            f"The largest product-level order changes were "
            f"{product_text}. "
        )

    elif product_text and driver == "average order value":

        summary += (
            f"Related product-level revenue movement during the period "
            f"was {product_text}. "
        )

    if positive_findings:

        positive = positive_findings[0]

        summary += (
            f"An important positive movement was also observed: "
            f"{positive.get('message', '')}. "
        )

    summary += (
        "The available sales data identifies the measurable pattern "
        "but does not establish the operational cause."
    )

    return summary


def _apply_analyst_synthesis(report, ai_insights):
    """
    Preserve AI-generated detailed analysis while making the two
    decision-oriented dashboard sections deterministic and concise.
    """
    result = dict(
        ai_insights or {}
    )

    result["executive_summary"] = _build_grounded_executive_summary(
        report
    )

    result["key_insights"] = _build_key_insights_from_findings(
        report
    )

    result["recommendations"] = _build_actionable_recommendations(
        report
    )

    # Final audit after deterministic synthesis and AI interpretation.
    for section_name in (
        "executive_summary",
        "key_insights",
        "product_insights",
        "customer_insights",
        "monthly_insights",
        "recommendations",
    ):

        if section_name == "executive_summary":

            result[section_name] = _audit_ai_text(
                result.get(section_name, "")
            )

        else:

            result[section_name] = [
                _audit_ai_text(item)
                for item in result.get(
                    section_name,
                    []
                )
            ]

    return result




def _audit_ai_text(text: str) -> str:
    """
    Conservative post-generation grounding audit.

    Replaces concepts that the current sales schema does not measure
    with safer terms rather than allowing unsupported business claims.
    """
    if not text:
        return text

    replacements = {
        "higher-ticket items": "higher average order value",
        "higher-ticket item": "higher average order value",
        "higher-priced items": "higher-revenue-per-order products",
        "higher-priced item": "higher-revenue-per-order product",
        "higher priced items": "higher-revenue-per-order products",
        "higher priced item": "higher-revenue-per-order product",
        "ticket size": "average order value",
        "cash flow": "sales performance",
        "cash flows": "sales performance",
        "profitability": "revenue performance",
        "profitable": "higher-revenue",
        "profit": "revenue",
        "margin": "revenue mix",
        "ROI": "measured sales impact",
        "return on investment": "measured sales impact",
    }

    audited = text

    for old_text, new_text in replacements.items():
        audited = audited.replace(old_text, new_text)
        audited = audited.replace(old_text.capitalize(), new_text)

    # Clean accidental duplicated terminal punctuation.
    while ".." in audited:
        audited = audited.replace("..", ".")

    # Keep the wording aligned with the available metrics.
    audited = audited.replace(
        "driven by an increase in average order value",
        "associated with an increase in average order value"
    )

    audited = audited.replace(
        "driven primarily by an increase in average order value",
        "associated primarily with an increase in average order value"
    )

    return audited



def _month_from_question(question: str):
    """Return (month_number, month_name) when a month is explicitly mentioned."""
    q = question.lower()

    month_map = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "sept": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }

    # Long names first so "may" etc. are handled naturally.
    for name, number in sorted(
        month_map.items(),
        key=lambda item: len(item[0]),
        reverse=True
    ):
        if re.search(rf"\b{re.escape(name)}\b", q):
            return number, calendar.month_name[number]

    return None, None


def _answer_month_product_question(
    report,
    question: str,
):
    """
    Answer month-specific product questions from the actual filtered
    transaction data, not from the whole-period product aggregate.
    """
    question_lower = question.lower()

    asks_product = (
        "product" in question_lower
        or "item" in question_lower
    )

    asks_best = any(
        phrase in question_lower
        for phrase in (
            "best",
            "top",
            "highest",
            "most revenue",
            "sold the most",
            "sold most",
            "most units",
            "most items",
            "most orders",
        )
    )

    month_number, month_name = _month_from_question(
        question
    )

    if not (
        asks_product
        and asks_best
        and month_number is not None
    ):
        return None

    sales_data = report.get("data")

    if sales_data is None or sales_data.empty:
        return (
            "There is no sales data available for that question."
        )

    month_rows = sales_data[
        sales_data["date"].dt.month == month_number
    ].copy()

    if month_rows.empty:
        return (
            f"I don't have any sales records for {month_name} "
            "in the current analysis."
        )

    # "Best product" means highest revenue unless the user explicitly
    # asks for units/items/orders.
    if (
        "units" in question_lower
        or "items" in question_lower
        or "quantity" in question_lower
        or "sold the most" in question_lower
        or "sold most" in question_lower
    ):
        product_metric = (
            month_rows.groupby("product")["quantity"]
            .sum()
            .sort_values(ascending=False)
        )

        if product_metric.empty:
            return (
                f"No product quantity data is available for {month_name}."
            )

        product = product_metric.index[0]
        value = product_metric.iloc[0]

        return (
            f"The top product by units sold in {month_name} was "
            f"{product}, with {int(value):,} units."
        )

    if (
        "orders" in question_lower
        or "order count" in question_lower
        or "most orders" in question_lower
    ):
        product_metric = (
            month_rows.groupby("product")["order_id"]
            .nunique()
            .sort_values(ascending=False)
        )

        if product_metric.empty:
            return (
                f"No product order data is available for {month_name}."
            )

        product = product_metric.index[0]
        value = product_metric.iloc[0]

        return (
            f"The top product by order count in {month_name} was "
            f"{product}, with {int(value):,} orders."
        )

    product_metric = (
        month_rows.groupby("product")["revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    product = product_metric.index[0]
    revenue = float(product_metric.iloc[0])

    total_month_revenue = float(
        month_rows["revenue"].sum()
    )

    share = (
        revenue / total_month_revenue * 100
        if total_month_revenue
        else 0
    )

    return (
        f"The best product by revenue in {month_name} was "
        f"{product} at ${revenue:,.2f}, contributing "
        f"{share:.2f}% of that month's revenue."
    )


def answer_sales_question(
    report,
    question: str,
) -> str:
    """
    Public Ask Your Data entry point.

    All natural-language questions go through the generic query planner
    and deterministic execution engine.
    """
    return _general_answer_sales_question(
        report,
        question,
    )


def _legacy_answer_sales_question(
    report,
    question: str,
) -> str:
    """
    Answer a user's question using verified report facts.

    Month-specific product questions are answered directly from the
    currently filtered transaction data so they respect the month named
    by the user.
    """

    question = (
        question
        or ""
    ).strip()

    if not question:
        return (
            "Please enter a question about your sales data."
        )

    # IMPORTANT:
    # Handle month-specific product questions BEFORE the whole-period
    # "top product" shortcut.
    month_product_answer = _answer_month_product_question(
        report,
        question
    )

    if month_product_answer:
        return month_product_answer

    kpis = report["kpis"]
    products = report["products"]
    customers = report["customers"]
    monthly = report["monthly"]

    business_findings = report.get(
        "business_findings",
        {}
    )

    priority_findings = business_findings.get(
        "priority_findings",
        []
    )

    positive_findings = business_findings.get(
        "positive_findings",
        []
    )

    product_context = "\n".join(
        [
            (
                f"{product}: orders={int(row['orders'])}, "
                f"items={int(row['quantity_sold'])}, "
                f"revenue=${row['revenue']:,.2f}, "
                f"revenue_share={row['revenue_percentage']:.2f}%"
            )
            for product, row in products.iterrows()
        ]
    )

    customer_context = "\n".join(
        [
            (
                f"{customer}: orders={int(row['orders'])}, "
                f"items={int(row['quantity_purchased'])}, "
                f"revenue=${row['revenue']:,.2f}, "
                f"revenue_share={row['revenue_percentage']:.2f}%"
            )
            for customer, row in customers.head(20).iterrows()
        ]
    )

    monthly_context = "\n".join(
        [
            (
                f"{month}: revenue=${row['revenue']:,.2f}, "
                f"orders={int(row['orders']):,}, "
                f"items={int(row['quantity']):,}, "
                f"AOV=${row['revenue'] / row['orders']:,.2f}"
            )
            for month, row in monthly.iterrows()
            if row["orders"] > 0
        ]
    )

    findings_context = "\n".join(
        [
            (
                f"- {finding.get('message', '')} | "
                f"driver={finding.get('primary_driver', '')} | "
                f"driver_products={finding.get('driver_product_text', '')} | "
                f"what_happened={finding.get('what_happened', '')} | "
                f"why_it_matters={finding.get('why_it_matters', '')}"
            )
            for finding in (
                priority_findings[:5]
                + positive_findings[:5]
            )
        ]
    )

    q = question.lower()

    # Whole-period lookup questions.
    if (
        ("top product" in q)
        or ("best product" in q)
        or ("highest revenue product" in q)
    ):
        top_product = products.index[0]
        top_revenue = products.iloc[0]["revenue"]
        share = products.iloc[0]["revenue_percentage"]

        return (
            f"{top_product} is the highest-revenue product in the "
            f"current analysis at ${top_revenue:,.2f}, contributing "
            f"{share:.2f}% of total revenue."
        )

    if (
        ("top customer" in q)
        or ("best customer" in q)
        or ("highest revenue customer" in q)
    ):
        top_customer = customers.index[0]
        top_revenue = customers.iloc[0]["revenue"]
        share = customers.iloc[0]["revenue_percentage"]

        return (
            f"{top_customer} is the highest-revenue customer in the "
            f"current analysis at ${top_revenue:,.2f}, contributing "
            f"{share:.2f}% of total revenue."
        )

    if (
        ("best month" in q)
        or ("strongest month" in q)
        or ("highest revenue month" in q)
    ):
        best_month = monthly["revenue"].idxmax()
        best_revenue = monthly.loc[
            best_month,
            "revenue"
        ]

        return (
            f"{best_month} is the strongest month at "
            f"${best_revenue:,.2f} in revenue."
        )

    if (
        ("worst month" in q)
        or ("weakest month" in q)
        or ("lowest revenue month" in q)
    ):
        worst_month = monthly["revenue"].idxmin()
        worst_revenue = monthly.loc[
            worst_month,
            "revenue"
        ]

        return (
            f"{worst_month} is the weakest month at "
            f"${worst_revenue:,.2f} in revenue."
        )

    if (
        ("why was" in q or "why is" in q or "why did" in q)
        and ("weak" in q or "drop" in q or "decline" in q)
        and priority_findings
    ):
        top = priority_findings[0]

        response = (
            f"The most important verified decline was "
            f"{top.get('message', '')} "
            f"The primary measurable driver was "
            f"{top.get('primary_driver', 'not isolated')}."
        )

        if top.get("driver_product_text"):
            response += (
                f" The leading product-level contributors were "
                f"{top['driver_product_text']}."
            )

        response += (
            " The data identifies the measurable pattern, "
            "but it does not establish the operational cause."
        )

        return response

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:

        if priority_findings:

            top = priority_findings[0]

            return (
                f"The highest-priority finding is "
                f"{top.get('message', '')} "
                f"The measurable driver is "
                f"{top.get('primary_driver', 'not isolated')}. "
                f"{top.get('why_it_matters', '')}"
            )

        return (
            f"The selected period generated "
            f"${kpis['total_revenue']:,.2f} across "
            f"{kpis['total_orders']:,} orders with an average "
            f"order value of "
            f"${kpis['average_order_value']:,.2f}."
        )

    prompt = f"""
You are an AI sales analyst.

Answer the user's question using ONLY the verified analytical context below.

USER QUESTION:
{question}

VERIFIED KPIs:
Revenue: ${kpis['total_revenue']:,.2f}
Orders: {kpis['total_orders']:,}
Items: {kpis['total_quantity']:,}
AOV: ${kpis['average_order_value']:,.2f}

MONTHLY:
{monthly_context}

PRODUCTS:
{product_context}

CUSTOMERS:
{customer_context}

BUSINESS SIGNALS:
{findings_context}

RULES:
1. Use only facts supported by the context.
2. Respect any specific month, date range, product, or customer named in
   the question.
3. If the question asks for a product within a specific month, use the
   monthly transaction context rather than the whole-period product ranking.
4. Do not invent causes.
5. Distinguish facts from reasonable inference.
6. If the data cannot answer the question, say so clearly.
7. Give a direct answer first, then the most relevant supporting numbers.
8. Keep the answer concise: 3-7 sentences unless a comparison requires more.
"""

    try:

        client = genai.Client(
            api_key=api_key
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "automatic_function_calling": {"disable": True},
            },
        )

        text = getattr(
            response,
            "text",
            ""
        )

        if text:
            return _audit_ai_text(
                text.strip()
            )

        return (
            "I could not generate an answer from the verified sales context."
        )

    except Exception as e:

        print(
            f"Ask Your Data failed: {e}"
        )

        return (
            "I couldn't generate the AI answer right now. "
            "Please use the Business Signals and Business Takeaways "
            "sections for the current verified findings."
        )



def generate_ai_insights(report):

    try:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            print("GEMINI_API_KEY not found.")
            return _apply_analyst_synthesis(
                report,
                generate_fallback_insights(report)
            )

        client = genai.Client(api_key=api_key)

        prompt = generate_ai_prompt(report)

        response_schema = {
            "type": "object",
            "properties": {
                "executive_summary": {
                    "type": "string"
                },
                "key_insights": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "product_insights": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "customer_insights": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "monthly_insights": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "executive_summary",
                "key_insights",
                "product_insights",
                "customer_insights",
                "monthly_insights",
                "recommendations"
            ]
        }

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "automatic_function_calling": {"disable": True},
                "response_mime_type": "application/json",
                "response_schema": response_schema
            }
        )

        audited_response = dict(
            response.parsed
        )

        audited_response["executive_summary"] = _audit_ai_text(
            audited_response.get(
                "executive_summary",
                ""
            )
        )

        for section_name in (
            "key_insights",
            "product_insights",
            "customer_insights",
            "monthly_insights",
            "recommendations",
        ):
            audited_response[section_name] = [
                _audit_ai_text(item)
                for item in audited_response.get(
                    section_name,
                    []
                )
            ]

        return _apply_analyst_synthesis(
            report,
            audited_response
        )

    except Exception as e:

        print(f"Gemini AI generation failed: {e}")
        print("Using fallback insights.")

        return _apply_analyst_synthesis(
            report,
            generate_fallback_insights(report)
        )

def generate_fallback_insights(report):

    kpis = report["kpis"]
    products = report["products"]
    customers = report["customers"]
    monthly = report["monthly"]

    business_findings = report.get(
        "business_findings",
        {}
    )

    priority_findings = business_findings.get(
        "priority_findings",
        []
    )

    positive_findings = business_findings.get(
        "positive_findings",
        []
    )

    best_product = products.index[0]
    best_product_revenue = products.iloc[0]["revenue"]

    worst_product = products.index[-1]
    worst_product_revenue = products.iloc[-1]["revenue"]

    highest_month = monthly["revenue"].idxmax()
    highest_month_revenue = monthly["revenue"].max()

    lowest_month = monthly["revenue"].idxmin()
    lowest_month_revenue = monthly["revenue"].min()

    top_customer = customers.index[0]
    top_customer_revenue = customers.iloc[0]["revenue"]

    # Build a synthesized deterministic summary.
    if priority_findings:

        top = priority_findings[0]

        top_message = top.get(
            "message",
            "A priority business change was detected."
        )

        driver = top.get(
            "primary_driver"
        )

        driver_phrase = ""

        if driver:
            driver_phrase = (
                f" The measurable driver was {driver}."
            )

        product_phrase = ""

        if top.get("driver_product_text"):
            product_phrase = (
                f" The main product-level contributors were "
                f"{top['driver_product_text']}."
            )

        positive_phrase = ""

        if positive_findings:
            positive_phrase = (
                f" By contrast, {positive_findings[0].get('message', '')}"
            )

        investigate_phrase = ""

        if top.get("investigate_next"):
            investigate_phrase = (
                f" The immediate next step is to "
                f"{top['investigate_next'].rstrip('.')}"
                "."
            )

        executive_summary = (
            f"{top_message}"
            f"{driver_phrase}"
            f"{product_phrase}"
            f"{positive_phrase}"
            f"{investigate_phrase}"
        )

    else:

        executive_summary = (
            f"The selected period generated "
            f"${kpis['total_revenue']:,.2f} across "
            f"{kpis['total_orders']:,} orders with an average "
            f"order value of ${kpis['average_order_value']:,.2f}. "
            f"{best_product} was the top revenue product at "
            f"${best_product_revenue:,.2f}, while "
            f"{highest_month} was the strongest month at "
            f"${highest_month_revenue:,.2f}."
        )

    key_insights = []

    for finding in priority_findings[:3]:

        insight = finding.get(
            "message",
            "Priority business signal detected."
        )

        driver = finding.get(
            "primary_driver"
        )

        if driver:
            insight += (
                f" The measurable driver was {driver}."
            )

        if finding.get("driver_product_text"):
            insight += (
                f" Product contributors: "
                f"{finding['driver_product_text']}."
            )

        key_insights.append(insight)

    if positive_findings:

        strongest_positive = positive_findings[0]

        key_insights.append(
            (
                f"{strongest_positive.get('message', '')} "
                f"The measurable driver was "
                f"{strongest_positive.get('primary_driver', 'the observed sales movement')}."
            )
        )

    if not key_insights:

        key_insights = [
            (
                f"{best_product} generated the highest product revenue "
                f"at ${best_product_revenue:,.2f}."
            ),
            (
                f"{highest_month} was the strongest month at "
                f"${highest_month_revenue:,.2f}, while "
                f"{lowest_month} was the weakest at "
                f"${lowest_month_revenue:,.2f}."
            )
        ]

    recommendations = []

    for finding in priority_findings[:3]:

        investigate = finding.get(
            "investigate_next",
            ""
        )

        if investigate:
            recommendations.append(
                investigate
            )

    # Keep fallback recommendations specific if there are no priority findings.
    if not recommendations:

        recommendations = [
            (
                f"Compare {highest_month} "
                f"(${highest_month_revenue:,.2f}) with "
                f"{lowest_month} (${lowest_month_revenue:,.2f}) "
                "to identify which orders, items, and product-mix changes "
                "most clearly distinguish a strong month from a weak month."
            ),
            (
                f"Evaluate {best_product}, which generated "
                f"${best_product_revenue:,.2f}, against lower-revenue products "
                "to identify a product-mix or upsell test worth running."
            ),
            (
                f"Compare the revenue trend for {top_customer}, at "
                f"${top_customer_revenue:,.2f}, with the broader customer base "
                "to identify whether customer concentration is increasing or declining."
            )
        ]

    return {
        "executive_summary": executive_summary,

        "key_insights": key_insights[:5],

        "product_insights": [
            (
                f"{best_product} was the highest-revenue product "
                f"at ${best_product_revenue:,.2f}."
            ),
            (
                f"{worst_product} generated the lowest product revenue "
                f"at ${worst_product_revenue:,.2f}."
            ),
            "Revenue performance does not indicate profitability "
            "because cost and margin data was not provided."
        ],

        "customer_insights": [
            (
                f"{top_customer} was the highest-revenue customer "
                f"at ${top_customer_revenue:,.2f}."
            ),
            "Customer revenue concentration should be monitored using "
            "the available customer-level revenue data."
        ],

        "monthly_insights": [
            (
                f"{highest_month} was the highest-revenue month "
                f"at ${highest_month_revenue:,.2f}."
            ),
            (
                f"{lowest_month} was the lowest-revenue month "
                f"at ${lowest_month_revenue:,.2f}."
            ),
            (
                "Monthly changes should be reviewed together with "
                "orders, items, and average order value."
            )
        ],

        "recommendations": recommendations[:3]
    }

# -------------------------
# Main program
# -------------------------

if __name__ == "__main__":

    from pdf_generator import generate_pdf

    file_path = "data/large_sales.csv"
    output_file = "output/business_report.pdf"

    try:

        print("Generating business report...")

        report = generate_report(file_path)

        print("Analyzing business data with Gemini...")

        ai_insights = generate_ai_insights(report)

        print("Generating PDF...")

        generate_pdf(
            report,
            output_file,
            ai_insights
        )

        print(
            f"Report created successfully: {output_file}"
        )

    except ValueError as e:

        print(str(e))

    except Exception as e:

        print(
            "\n❌ Something unexpected happened "
            "while generating the report."
        )

        print(f"Details: {e}")