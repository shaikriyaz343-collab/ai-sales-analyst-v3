
from __future__ import annotations
from typing import Any
import pandas as pd

def _issue(severity, code, message, affected_rows=0, recommendation=""):
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "affected_rows": int(affected_rows),
        "recommendation": recommendation,
    }

def run_data_quality_checks(data: pd.DataFrame, semantic_model: dict[str, Any]) -> dict[str, Any]:
    issues = []
    core = {
        "date": "Date",
        "order_id": "Order / Transaction ID",
        "customer": "Customer",
        "product": "Product",
        "quantity": "Quantity",
    }

    for field, label in core.items():
        if field in data.columns:
            missing = int(data[field].isna().sum())
            if missing:
                issues.append(_issue(
                    "critical" if field in {"date", "order_id"} else "warning",
                    f"MISSING_{field.upper()}",
                    f"{label} is missing in {missing:,} row(s).",
                    missing,
                    f"Review the {label.lower()} column."
                ))

    if "order_id" in data.columns:
        dup = int(data["order_id"].duplicated(keep=False).sum())
        if dup:
            issues.append(_issue(
                "warning",
                "DUPLICATE_ORDER_ID",
                f"{dup:,} row(s) share a duplicate order/transaction ID.",
                dup,
                "Confirm whether repeated IDs are valid line items."
            ))

    if "quantity" in data.columns:
        q = pd.to_numeric(data["quantity"], errors="coerce")
        bad = int((q.isna() | (q <= 0)).sum())
        if bad:
            issues.append(_issue(
                "warning",
                "INVALID_QUANTITY",
                f"{bad:,} row(s) contain missing or non-positive quantity.",
                bad,
                "Review quantity values."
            ))

    for field, label in [("revenue","Revenue"),("price","Unit Price"),
                         ("cost","Cost"),("discount_amount","Discount Amount"),
                         ("return_amount","Return Amount")]:
        if field in data.columns:
            v = pd.to_numeric(data[field], errors="coerce")
            neg = int((v < 0).sum())
            if neg:
                issues.append(_issue(
                    "info",
                    f"NEGATIVE_{field.upper()}",
                    f"{neg:,} row(s) contain negative {label.lower()} values.",
                    neg,
                    "Confirm whether negatives represent refunds, credits, or corrections."
                ))

    if "date" in data.columns:
        d = pd.to_datetime(data["date"], errors="coerce")
        bad = int(d.isna().sum())
        if bad:
            issues.append(_issue(
                "critical", "INVALID_DATE",
                f"{bad:,} row(s) contain invalid dates.",
                bad,
                "Correct invalid dates before period analysis."
            ))

    if {"quantity","price","revenue"}.issubset(data.columns):
        q = pd.to_numeric(data["quantity"], errors="coerce")
        p = pd.to_numeric(data["price"], errors="coerce")
        r = pd.to_numeric(data["revenue"], errors="coerce")
        comparable = q.notna() & p.notna() & r.notna()
        if comparable.any():
            expected = q[comparable] * p[comparable]
            mismatch = ((expected - r[comparable]).abs() > 0.01)
            bad = int(mismatch.sum())
            if bad:
                issues.append(_issue(
                    "warning", "REVENUE_MISMATCH",
                    f"{bad:,} row(s) do not reconcile as Quantity × Unit Price = Revenue.",
                    bad,
                    "Check discounts, taxes, shipping, or net-sales adjustments."
                ))

    if "discount_pct" in data.columns:
        d = pd.to_numeric(data["discount_pct"], errors="coerce")
        bad = int(((d < 0) | (d > 100)).sum())
        if bad:
            issues.append(_issue(
                "warning", "INVALID_DISCOUNT",
                f"{bad:,} row(s) contain discount percentages outside 0–100%.",
                bad,
                "Confirm whether discounts are stored as percentages or decimals."
            ))

    critical = sum(i["severity"] == "critical" for i in issues)
    warning = sum(i["severity"] == "warning" for i in issues)

    status = "needs_review" if critical else "usable_with_warnings" if warning else "good"

    return {
        "row_count": len(data),
        "issue_count": len(issues),
        "critical_count": critical,
        "warning_count": warning,
        "info_count": sum(i["severity"] == "info" for i in issues),
        "quality_status": status,
        "issues": issues,
    }


def quality_summary(result: dict[str, Any]) -> str:
    status = result.get("quality_status", "unknown")

    if status == "good":
        return "Data quality looks good for analysis."

    if status == "usable_with_warnings":
        return (
            "The data can be analyzed, but a few items should be reviewed."
        )

    if status == "needs_review":
        return (
            "Some data-quality issues may affect the accuracy of the analysis."
        )

    return "Data quality status is not available."
