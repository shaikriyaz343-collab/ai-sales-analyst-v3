
from __future__ import annotations

from typing import Any

import pandas as pd


def _num(series):
    return pd.to_numeric(series, errors="coerce")


def _pct(numerator, denominator):
    if denominator in (0, None):
        return None
    return float(numerator / denominator * 100)


def _group_sum(data, group_col, value_col, limit=10):
    if group_col not in data.columns or value_col not in data.columns:
        return []
    grouped = (
        data.groupby(group_col, dropna=False)[value_col]
        .sum()
        .sort_values(ascending=False)
        .head(limit)
    )
    return grouped.reset_index(name=value_col).to_dict("records")


def analyze_sales_pipeline(data: pd.DataFrame) -> dict[str, Any]:
    """Analyze opportunity pipeline using open/closed semantics."""
    stage_col = next((c for c in ["stage", "opportunity_stage"] if c in data.columns), None)
    amount_col = next((c for c in ["amount", "pipeline_amount", "revenue"] if c in data.columns), None)
    salesperson_col = "salesperson" if "salesperson" in data.columns else None

    available = stage_col is not None and amount_col is not None
    result = {
        "module": "pipeline",
        "title": "Sales Pipeline",
        "available": available,
        "metrics": {},
        "stage_breakdown": [],
        "salesperson_breakdown": [],
        "insights": [],
    }
    if not available:
        return result

    amount = _num(data[amount_col]).fillna(0)
    stage_text = data[stage_col].astype(str).str.strip().str.lower()
    won = stage_text.str.contains(r"won|closed won|success", regex=True)
    lost = stage_text.str.contains(r"lost|closed lost|failed", regex=True)
    open_mask = ~(won | lost)

    if "opportunity_id" in data.columns:
        opp_key = data["opportunity_id"]
    elif "order_id" in data.columns:
        opp_key = data["order_id"]
    else:
        opp_key = pd.Series(range(len(data)), index=data.index)

    result["metrics"] = {
        "pipeline_value": float(amount.sum()),
        "open_pipeline_value": float(amount[open_mask].sum()),
        "won_value": float(amount[won].sum()),
        "lost_value": float(amount[lost].sum()),
        "opportunities": int(opp_key.nunique()),
        "open_opportunities": int(opp_key[open_mask].nunique()),
        "won_opportunities": int(opp_key[won].nunique()),
        "lost_opportunities": int(opp_key[lost].nunique()),
        "win_rate_pct": _pct(amount[won].sum(), amount[won | lost].sum()),
        "value_win_rate_pct": _pct(amount[won].sum(), amount[won | lost].sum()),
    }

    stage_values = (
        data.loc[open_mask].assign(_amount=amount[open_mask])
        .groupby(stage_col)["_amount"].sum()
        .sort_values(ascending=False)
    )
    result["stage_breakdown"] = stage_values.reset_index(name="amount").to_dict("records")

    if salesperson_col:
        reps = (
            data.loc[open_mask].assign(_amount=amount[open_mask])
            .groupby(salesperson_col)["_amount"].sum()
            .sort_values(ascending=False).head(10)
        )
        result["salesperson_breakdown"] = reps.reset_index(name="amount").to_dict("records")

    return result


def analyze_sales_forecast(data: pd.DataFrame) -> dict[str, Any]:
    """Build an open-pipeline forecast only from open opportunities."""
    close_col = next((c for c in ["expected_close", "close_date"] if c in data.columns), None)
    amount_col = next((c for c in ["amount", "pipeline_amount", "revenue"] if c in data.columns), None)
    probability_col = next((c for c in ["probability", "win_probability"] if c in data.columns), None)

    result = {"module": "forecast", "title": "Sales Forecast", "available": False,
              "metrics": {}, "monthly_forecast": [], "notes": []}
    if close_col is None or amount_col is None or "stage" not in data.columns and "opportunity_stage" not in data.columns:
        return result

    stage_col = "stage" if "stage" in data.columns else "opportunity_stage"
    dates = pd.to_datetime(data[close_col], errors="coerce")
    amount = _num(data[amount_col]).fillna(0)
    stage_text = data[stage_col].astype(str).str.strip().str.lower()
    won = stage_text.str.contains(r"won|closed won|success", regex=True)
    lost = stage_text.str.contains(r"lost|closed lost|failed", regex=True)
    open_mask = ~(won | lost)
    valid = dates.notna() & open_mask
    if not valid.any():
        return result

    clean = pd.DataFrame({"_date": dates[valid], "_amount": amount[valid]})
    if probability_col:
        probability = _num(data.loc[valid, probability_col]).fillna(0)
        if probability.max() > 1:
            probability = probability / 100.0
        probability = probability.clip(0, 1)
        clean["_probability"] = probability
        clean["_weighted"] = clean["_amount"] * clean["_probability"]
        has_probability = True
    else:
        clean["_probability"] = 1.0
        clean["_weighted"] = clean["_amount"]
        has_probability = False
        result["notes"].append("No probability field was found; weighted forecast equals open expected value.")

    result["available"] = True
    result["metrics"] = {
        "has_probability": has_probability,
        "open_pipeline_value": float(clean["_amount"].sum()),
        "pipeline_value": float(amount[dates.notna()].sum()),
        "weighted_forecast": float(clean["_weighted"].sum()),
        "opportunities": int(len(clean)),
        "open_opportunities": int(len(clean)),
    }

    monthly = (
        clean.assign(month=clean["_date"].dt.to_period("M").astype(str))
        .groupby("month")
        .agg(expected_value=("_amount", "sum"), weighted_forecast=("_weighted", "sum"), opportunities=("_amount", "size"))
        .reset_index().sort_values("month")
    )
    result["monthly_forecast"] = monthly.to_dict("records")
    return result

def analyze_subscription_business(data: pd.DataFrame) -> dict[str, Any]:
    """Analyze subscription data using the latest dated snapshot when available."""
    mrr_col = next((c for c in ["mrr", "monthly_recurring_revenue"] if c in data.columns), None)
    customer_col = "customer" if "customer" in data.columns else None
    churn_col = next((c for c in ["churn_status", "churn"] if c in data.columns), None)
    available = mrr_col is not None and (customer_col is not None or churn_col is not None)
    result = {"module":"subscription","title":"Recurring Revenue","available":available,"metrics":{},"customer_breakdown":[],"insights":[]}
    if not available:
        return result

    snapshot = data.copy()
    snapshot_label = None
    if "date" in snapshot.columns:
        dt = pd.to_datetime(snapshot["date"], errors="coerce")
        valid = snapshot.loc[dt.notna()].copy()
        if not valid.empty and valid["date"].nunique() > 1:
            latest_date = pd.to_datetime(valid["date"], errors="coerce").max()
            snapshot = valid[pd.to_datetime(valid["date"], errors="coerce") == latest_date].copy()
            snapshot_label = latest_date.strftime("%B %d, %Y")
        elif not valid.empty:
            snapshot_label = pd.to_datetime(valid["date"], errors="coerce").max().strftime("%B %d, %Y")

    mrr = _num(snapshot[mrr_col]).fillna(0)
    total_mrr = float(mrr.sum())
    result["metrics"]["mrr"] = total_mrr
    result["metrics"]["annualized_revenue"] = total_mrr * 12
    result["metrics"]["snapshot_label"] = snapshot_label

    if customer_col:
        customer_mrr = snapshot.assign(_mrr=mrr).groupby(customer_col)["_mrr"].sum().sort_values(ascending=False).head(10)
        result["customer_breakdown"] = customer_mrr.reset_index(name="mrr").to_dict("records")

    if churn_col:
        churn = snapshot[churn_col].astype(str).str.strip().str.lower()
        churned = churn.str.contains(r"churn|cancel|inactive", regex=True)
        result["metrics"]["churn_rate_pct"] = float(churned.mean() * 100) if len(churned) else None
        if customer_col:
            total_customers = snapshot[customer_col].nunique()
            churned_customers = snapshot.loc[churned, customer_col].nunique()
            result["metrics"]["churned_customer_rate_pct"] = (
                float(churned_customers / total_customers * 100) if total_customers else None
            )
            result["metrics"]["churned_customers"] = int(churned_customers)
        result["metrics"]["churned_records"] = int(churned.sum())

    # Keep snapshot data internal for concentration analysis; callers should not render it directly.
    result["_snapshot_data"] = snapshot
    return result


def analyze_services_business(data: pd.DataFrame) -> dict[str, Any]:
    """Analyze professional-services data and use consistent billing semantics."""
    hours_col = next((c for c in ["hours", "billable_hours", "hours_billed"] if c in data.columns), None)
    revenue_col = next((c for c in ["revenue", "billings", "billing", "amount"] if c in data.columns), None)
    client_col = next((c for c in ["customer", "client"] if c in data.columns), None)
    employee_col = next((c for c in ["employee", "consultant", "salesperson"] if c in data.columns), None)
    available = hours_col is not None and revenue_col is not None
    result = {"module":"services","title":"Services & Billings","available":available,"metrics":{},"client_breakdown":[],"employee_breakdown":[],"insights":[]}
    if not available:
        return result

    hours = _num(data[hours_col]).fillna(0)
    revenue = _num(data[revenue_col]).fillna(0)
    result["metrics"] = {
        "hours": float(hours.sum()),
        "billings": float(revenue.sum()),
        "revenue_per_hour": float(revenue.sum() / hours.sum()) if hours.sum() else None,
    }
    if client_col:
        client = data.assign(_revenue=revenue).groupby(client_col)["_revenue"].sum().sort_values(ascending=False).head(10)
        result["client_breakdown"] = client.reset_index(name="revenue").to_dict("records")
    if employee_col:
        employee = data.assign(_hours=hours).groupby(employee_col)["_hours"].sum().sort_values(ascending=False).head(10)
        result["employee_breakdown"] = employee.reset_index(name="hours").to_dict("records")
    return result


def run_business_type_packs(
    data: pd.DataFrame,
    business_type: dict[str, Any],
) -> dict[str, Any]:

    primary = business_type.get(
        "primary_type"
    )

    packs = {}

    if primary == "transactional_sales":
        # Core retail/transactional work is handled by the adaptive analysis
        # engine. This function still returns a consistent pack container.
        packs["transactional_sales"] = {
            "module": "transactional_sales",
            "available": True,
            "title": "Transactional Sales",
        }

    elif primary == "sales_pipeline":
        packs["sales_pipeline"] = analyze_sales_pipeline(
            data
        )
        packs["forecast"] = analyze_sales_forecast(
            data
        )

    elif primary == "subscription":
        packs["subscription"] = analyze_subscription_business(
            data
        )

    elif primary == "services":
        packs["services"] = analyze_services_business(
            data
        )

    return {
        "primary_type": primary,
        "packs": packs,
    }
