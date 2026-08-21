
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable

import pandas as pd


@dataclass
class InvestigationStep:
    name: str
    status: str
    finding: str
    evidence: dict[str, Any]


@dataclass
class BusinessAgentResult:
    question: str
    intent: str
    executive_answer: str
    steps: list[dict[str, Any]]
    recommendations: list[str]
    confidence: str
    limitations: list[str]


def _num(series):
    return pd.to_numeric(series, errors="coerce")


def _pct_change(current, previous):
    if previous in (0, None):
        return None
    return float(
        (current - previous)
        / abs(previous)
        * 100
    )


def _period_label(period):
    try:
        return str(period)
    except Exception:
        return "selected period"


def _monthly_table(data):
    if "date" not in data.columns or "revenue" not in data.columns:
        return pd.DataFrame()

    w=data.copy()
    w["_month"]=pd.to_datetime(
        w["date"],
        errors="coerce",
    ).dt.to_period("M").astype(str)

    w=w.dropna(subset=["_month"])

    agg={
        "revenue":("revenue","sum"),
    }

    if "order_id" in w.columns:
        agg["orders"]=("order_id","nunique")
    else:
        agg["orders"]=("revenue","size")

    m=w.groupby("_month").agg(**agg).reset_index()

    if "quantity" in w.columns:
        q=w.groupby("_month")["quantity"].sum().reset_index(name="quantity")
        m=m.merge(q,on="_month",how="left")

    m["aov"]=m["revenue"]/m["orders"].replace(0,pd.NA)
    return m.sort_values("_month")


def _intent(question: str) -> str:
    q=question.lower()

    if any(x in q for x in [
        "why", "what caused", "reason", "decline", "drop",
        "fell", "weaker", "weak",
    ]):
        return "investigate_change"

    if any(x in q for x in [
        "best", "top", "highest", "most", "lowest", "worst",
    ]):
        return "rank"

    if any(x in q for x in [
        "compare", "versus", "vs", "compared",
    ]):
        return "compare"

    return "answer"


def _investigate_change(
    data: pd.DataFrame,
    question: str,
) -> BusinessAgentResult:

    steps: list[InvestigationStep] = []
    limitations: list[str] = []

    monthly=_monthly_table(data)

    if len(monthly)<2:
        return BusinessAgentResult(
            question=question,
            intent="investigate_change",
            executive_answer=(
                "I need at least two comparable periods to investigate "
                "a business change."
            ),
            steps=[],
            recommendations=[],
            confidence="low",
            limitations=[
                "The data does not contain at least two comparable periods."
            ],
        )

    previous=monthly.iloc[-2]
    current=monthly.iloc[-1]

    revenue_pct=_pct_change(
        current["revenue"],
        previous["revenue"],
    )

    orders_pct=_pct_change(
        current["orders"],
        previous["orders"],
    )

    aov_pct=_pct_change(
        current["aov"],
        previous["aov"],
    )

    steps.append(
        InvestigationStep(
            name="period_change",
            status="complete",
            finding=(
                f"Revenue changed {revenue_pct:+.1f}% from "
                f"{_period_label(previous['_month'])} to "
                f"{_period_label(current['_month'])}."
            ),
            evidence={
                "previous_period": str(previous["_month"]),
                "current_period": str(current["_month"]),
                "revenue_previous": float(previous["revenue"]),
                "revenue_current": float(current["revenue"]),
                "revenue_change_pct": revenue_pct,
            },
        )
    )

    # Determine the dominant measurable driver.
    if (
        orders_pct is not None
        and aov_pct is not None
    ):
        driver = (
            "order volume"
            if abs(orders_pct) > abs(aov_pct)
            else "average order value"
        )

        steps.append(
            InvestigationStep(
                name="driver_check",
                status="complete",
                finding=(
                    f"The stronger measurable driver was {driver}: "
                    f"orders changed {orders_pct:+.1f}% while AOV changed "
                    f"{aov_pct:+.1f}%."
                ),
                evidence={
                    "orders_change_pct": orders_pct,
                    "aov_change_pct": aov_pct,
                    "driver": driver,
                },
            )
        )
    else:
        driver=None

    # Product investigation.
    if (
        "product" in data.columns
        and "revenue" in data.columns
    ):

        w=data.copy()
        w["_month"]=pd.to_datetime(
            w["date"],
            errors="coerce",
        ).dt.to_period("M").astype(str)

        current_month=str(current["_month"])
        previous_month=str(previous["_month"])

        current_products=(
            w[w["_month"]==current_month]
            .groupby("product")["revenue"]
            .sum()
        )

        previous_products=(
            w[w["_month"]==previous_month]
            .groupby("product")["revenue"]
            .sum()
        )

        delta=(
            current_products
            .sub(
                previous_products,
                fill_value=0,
            )
            .sort_values()
        )

        drags=[
            {
                "product":str(name),
                "change":float(value),
            }
            for name,value in delta.head(3).items()
            if value<0
        ]

        if drags:
            top=drags[0]
            steps.append(
                InvestigationStep(
                    name="product_contributors",
                    status="complete",
                    finding=(
                        f"The largest product-level revenue decline came "
                        f"from {top['product']} ({top['change']:+.2f})."
                    ),
                    evidence={
                        "top_declines":drags,
                    },
                )
            )

    # Customer investigation.
    if (
        "customer" in data.columns
        and "revenue" in data.columns
    ):

        current_customers=(
            w[w["_month"]==current_month]
            .groupby("customer")["revenue"]
            .sum()
        )

        previous_customers=(
            w[w["_month"]==previous_month]
            .groupby("customer")["revenue"]
            .sum()
        )

        delta=(
            current_customers
            .sub(
                previous_customers,
                fill_value=0,
            )
            .sort_values()
        )

        drags=[
            {
                "customer":str(name),
                "change":float(value),
            }
            for name,value in delta.head(3).items()
            if value<0
        ]

        if drags:
            top=drags[0]
            steps.append(
                InvestigationStep(
                    name="customer_contributors",
                    status="complete",
                    finding=(
                        f"The largest customer-level revenue decline came "
                        f"from {top['customer']} ({top['change']:+.2f})."
                    ),
                    evidence={
                        "top_declines":drags,
                    },
                )
            )

    # Optional return check.
    if "return_status" in data.columns:

        result_flags=(
            data["return_status"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin({
                "returned","return","yes","y",
                "true","refunded","refund",
            })
        )

        return_rate=float(
            result_flags.mean()*100
        )

        steps.append(
            InvestigationStep(
                name="return_check",
                status="complete",
                finding=(
                    f"Return rate in the available data is "
                    f"{return_rate:.1f}%."
                ),
                evidence={
                    "return_rate_pct":return_rate,
                },
            )
        )

    # Optional discount check.
    if "discount_pct" in data.columns:

        discounts=_num(
            data["discount_pct"]
        )

        avg_discount=float(
            discounts.mean()
        )

        steps.append(
            InvestigationStep(
                name="discount_check",
                status="complete",
                finding=(
                    f"Average discount in the available data is "
                    f"{avg_discount:.1f}%."
                ),
                evidence={
                    "average_discount_pct":avg_discount,
                },
            )
        )

    answer_parts=[]

    direction=(
        "increased"
        if revenue_pct>0
        else "decreased"
        if revenue_pct<0
        else "was unchanged"
    )

    answer_parts.append(
        f"Revenue {direction} {abs(revenue_pct):.1f}% from "
        f"{previous['_month']} to {current['_month']}."
    )

    if driver:
        answer_parts.append(
            f"The strongest measurable driver was {driver}."
        )

    # Pull top product/customer findings from the investigation.
    product_step=next(
        (
            s for s in steps
            if s.name=="product_contributors"
        ),
        None,
    )

    if product_step:
        top=product_step.evidence["top_declines"][0]
        answer_parts.append(
            f"{top['product']} had the largest product-level revenue decline."
        )

    customer_step=next(
        (
            s for s in steps
            if s.name=="customer_contributors"
        ),
        None,
    )

    if customer_step:
        top=customer_step.evidence["top_declines"][0]
        answer_parts.append(
            f"{top['customer']} had the largest customer-level revenue decline."
        )

    limitations.append(
        "The analysis identifies measurable patterns in the sales data; "
        "it does not establish operational or external causes unless those "
        "data sources are available."
    )

    recommendations=[]

    if driver=="order volume":
        recommendations.append(
            "Investigate why order volume changed in the weaker period."
        )

    elif driver=="average order value":
        recommendations.append(
            "Investigate changes in basket size, pricing, product mix, or discounting."
        )

    if product_step:
        recommendations.append(
            "Review the top product-level revenue declines."
        )

    if customer_step:
        recommendations.append(
            "Review customers with the largest revenue declines."
        )

    return BusinessAgentResult(
        question=question,
        intent="investigate_change",
        executive_answer=" ".join(answer_parts),
        steps=[
            asdict(step)
            for step in steps
        ],
        recommendations=recommendations,
        confidence=(
            "high"
            if len(steps)>=3
            else "medium"
        ),
        limitations=limitations,
    )


def answer_with_agent(
    data: pd.DataFrame,
    question: str,
) -> dict[str, Any]:

    question=(
        question
        or ""
    ).strip()

    if not question:
        return asdict(
            BusinessAgentResult(
                question="",
                intent="answer",
                executive_answer=(
                    "Please enter a business question."
                ),
                steps=[],
                recommendations=[],
                confidence="low",
                limitations=[],
            )
        )

    intent=_intent(
        question
    )

    if intent=="investigate_change":
        result=_investigate_change(
            data,
            question,
        )
        return asdict(result)

    # For simple questions, the existing query engine remains the preferred
    # deterministic calculation path. This function deliberately does not
    # invent a metric when the orchestration path is not implemented.
    return asdict(
        BusinessAgentResult(
            question=question,
            intent=intent,
            executive_answer=(
                "This question should be handled by the deterministic "
                "Ask Your Business Analyst query engine."
            ),
            steps=[],
            recommendations=[],
            confidence="high",
            limitations=[],
        )
    )
