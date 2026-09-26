from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from adaptive_analysis_engine_v1 import (
    analyze_core_performance,
    analyze_customers,
    analyze_dimension,
    analyze_discounts,
    analyze_products,
    analyze_returns,
)
from business_analysis_packs_v1 import (
    analyze_sales_forecast,
    analyze_sales_pipeline,
    analyze_services_business,
    analyze_subscription_business,
)
from business_type_detector_v1 import detect_business_type
from schema_profiler_v2 import load_dataframe, profile_dataframe
from semantic_business_model_v2 import build_semantic_model

from ..contracts import Evidence, OverviewInsight, OverviewMetric, OverviewResponse
from ..runtime_persistence import runtime_object_store
from .onboarding import STORAGE, get_dataset
from .session import apply_scope, scope_label


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _canonicalize(data: pd.DataFrame, profile: dict[str, Any]) -> pd.DataFrame:
    out = data.copy()
    for semantic_name, columns in profile.get("recognized", {}).items():
        if not columns:
            continue
        source = columns[0]
        if source in out.columns and semantic_name not in out.columns:
            out[semantic_name] = out[source]
    if "revenue" not in out.columns and {"quantity", "price"}.issubset(out.columns):
        adjustments = {"discount_pct", "discount_amount", "tax_amount", "shipping_amount"}
        if not adjustments.intersection(profile.get("recognized", {})):
            out["revenue"] = _num(out["quantity"]) * _num(out["price"])
    return out


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    value = float(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.1f}K"
    return f"{sign}${value:,.0f}"


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{float(value):.1f}%"


def _count(value: float | int | None) -> str:
    return "—" if value is None else f"{float(value):,.0f}"


def _ev(metric: str, value: float | None, calculation: str, fields: list[str], comparison: float | None = None) -> Evidence:
    return Evidence(metric=metric, value=value, comparison_value=comparison, calculation=calculation, source_fields=fields)


def _metric(metric_id: str, label: str, value: float | None, display: str, calculation: str, fields: list[str], *, delta: float | None = None, delta_label: str | None = None, tone: str = "neutral", comparison: float | None = None) -> OverviewMetric:
    return OverviewMetric(
        id=metric_id,
        label=label,
        value=value,
        display_value=display,
        delta_pct=delta,
        delta_label=delta_label,
        tone=tone,
        evidence=_ev(metric_id, value, calculation, fields, comparison),
    )


def _insight(insight_id: str, severity: str, title: str, summary: str, why: str, action: str, metric: str, value: float | None, calculation: str, fields: list[str]) -> OverviewInsight:
    return OverviewInsight(
        id=insight_id,
        severity=severity,
        title=title,
        summary=summary,
        why_it_matters=why,
        recommendation=action,
        evidence=_ev(metric, value, calculation, fields),
    )


def build_overview(dataset_id: str, scope=None) -> OverviewResponse:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")

    suffix = Path(summary.file_name).suffix.lower()
    path = runtime_object_store(local_root=STORAGE).path_for(f"{dataset_id}{suffix}")
    if not path.exists():
        raise ValueError("Dataset file is no longer available for analysis.")

    data = load_dataframe(path)
    profile = profile_dataframe(data)
    semantic = build_semantic_model(profile, data=data)
    business = detect_business_type(semantic, profile)
    canonical = _canonicalize(data, profile)
    if scope is not None:
        canonical = apply_scope(canonical, scope)
    primary = business.get("primary_type")

    metrics: list[OverviewMetric] = []
    attention: list[OverviewInsight] = []
    opportunities: list[OverviewInsight] = []
    what_changed: list[str] = []

    if primary == "transactional_sales":
        perf = analyze_core_performance(canonical)
        returns = analyze_returns(canonical)
        products = analyze_products(canonical)
        customers = analyze_customers(canonical)
        discounts = analyze_discounts(canonical)
        pm = perf.get("metrics", {})
        revenue, orders, aov = pm.get("revenue"), pm.get("orders"), pm.get("aov")
        return_metrics = returns.get("metrics", {})
        return_rate = return_metrics.get("returned_order_rate_pct")
        if return_rate is None:
            return_rate = return_metrics.get("return_rate_pct")

        metrics = [
            _metric("revenue", "Revenue", revenue, _money(revenue), "sum(revenue)", ["revenue"]),
            _metric("orders", "Orders", orders, _count(orders), "distinct order_id count", ["order_id"]),
            _metric("aov", "AOV", aov, _money(aov), "revenue / distinct orders", ["revenue", "order_id"]),
        ]
        if return_rate is not None:
            metrics.append(_metric("return_rate", "Return rate", return_rate, _pct(return_rate), "returned orders / total orders × 100", ["return_status", "order_id"], tone="risk" if return_rate >= 10 else "neutral"))

        monthly = perf.get("monthly") or []
        if len(monthly) >= 2:
            prev, cur = monthly[-2], monthly[-1]
            previous_revenue = float(prev.get("revenue") or 0)
            current_revenue = float(cur.get("revenue") or 0)
            delta = None if previous_revenue == 0 else (current_revenue - previous_revenue) / abs(previous_revenue) * 100
            metrics[0].delta_pct = delta
            metrics[0].delta_label = f"{prev.get('_month')} → {cur.get('_month')}"
            metrics[0].evidence.comparison_value = previous_revenue
            direction = "increased" if current_revenue >= previous_revenue else "decreased"
            what_changed.append(f"Revenue {direction} {abs(delta):.1f}% ({prev.get('_month')} → {cur.get('_month')})." if delta is not None else "Revenue has a comparable monthly history.")
            if perf.get("insights"):
                driver = perf["insights"][-1].get("driver")
                if driver:
                    what_changed.append(f"The larger movement came from {driver}.")
        elif len(monthly) == 1:
            what_changed.append(f"Latest revenue is {_money(float(monthly[-1].get('revenue') or 0))} for {monthly[-1].get('_month')}.")

        if return_rate is not None and return_rate >= 10:
            attention.append(_insight(
                "return-rate-risk", "high", f"Return rate is {return_rate:.1f}%",
                "Returns are elevated enough to warrant investigation.",
                "Returns can erode realized revenue and may indicate product or fulfillment issues.",
                "Investigate returned orders by product and region before changing inventory or promotion plans.",
                "return_rate", return_rate, "returned orders / total orders × 100", ["return_status", "order_id"],
            ))
        share = (customers.get("concentration") or {}).get("top_customer_revenue_share_pct")
        if share is not None and share >= 50:
            attention.append(_insight(
                "customer-concentration", "medium", f"Top customer is {share:.1f}% of revenue",
                "Revenue concentration is high in a single customer.",
                "A concentrated revenue base increases exposure if one account reduces spend or leaves.",
                "Review the top account's recent activity and build a diversification plan.",
                "customer_revenue_share", share, "top customer revenue / total revenue × 100", ["customer", "revenue"],
            ))
        top_product = products.get("concentration") or {}
        if top_product.get("top_product"):
            share = top_product.get("top_product_revenue_share_pct")
            opportunities.append(_insight(
                "top-product", "info", f"{top_product['top_product']} is the leading product",
                f"It contributes {share:.1f}% of observed revenue." if share is not None else "It is the leading product by revenue.",
                "Leading products can inform inventory, cross-sell and targeted commercial activity.",
                f"Review customers and regions buying {top_product['top_product']} and identify expansion opportunities.",
                "product_revenue_share", share, "top product revenue / total revenue × 100", ["product", "revenue"],
            ))
        avg_discount = discounts.get("metrics", {}).get("average_discount_pct")
        if avg_discount is not None:
            metrics.append(_metric("average_discount", "Avg discount", avg_discount, _pct(avg_discount), "mean(discount_pct)", ["discount_pct"]))

    elif primary == "sales_pipeline":
        pipeline = analyze_sales_pipeline(canonical)
        forecast = analyze_sales_forecast(canonical)
        pm, fm = pipeline.get("metrics", {}), forecast.get("metrics", {})
        pipeline_value, weighted, win_rate = pm.get("pipeline_value"), fm.get("weighted_forecast"), pm.get("win_rate_pct")
        metrics = [
            _metric("pipeline_value", "Pipeline", pipeline_value, _money(pipeline_value), "sum(opportunity amount)", ["amount"]),
            _metric("weighted_forecast", "Weighted forecast", weighted, _money(weighted), "sum(open amount × probability)", ["amount", "probability"]),
            _metric("win_rate", "Win rate", win_rate, _pct(win_rate), "won amount / (won amount + lost amount) × 100", ["amount", "stage"], tone="risk" if win_rate is not None and win_rate < 50 else "neutral"),
        ]
        if pm.get("open_pipeline_value") is not None:
            what_changed.append(f"Open pipeline is {_money(pm['open_pipeline_value'])} of {_money(pipeline_value)} total pipeline.")
        if fm.get("monthly_forecast"):
            what_changed.append(f"Forecast coverage is available across {len(fm['monthly_forecast'])} expected-close period(s).")
        if win_rate is not None and win_rate < 50:
            attention.append(_insight(
                "win-rate-risk", "high", f"Win rate is {win_rate:.1f}%",
                "Closed opportunity outcomes are converting below a 50% rate.",
                "Low conversion reduces realized revenue from the current opportunity pool.",
                "Review lost opportunities by stage and salesperson before increasing acquisition spend.",
                "win_rate", win_rate, "won amount / (won amount + lost amount) × 100", ["amount", "stage"],
            ))
        if weighted is not None and pipeline_value:
            coverage = weighted / pipeline_value * 100
            if coverage < 50:
                attention.append(_insight(
                    "forecast-risk", "medium", f"Weighted coverage is {coverage:.1f}% of pipeline",
                    "A relatively small share of total pipeline is probability-weighted into the current forecast.",
                    "More pipeline therefore depends on lower-probability opportunities.",
                    "Prioritize stalled and lower-probability deals with the strongest evidence of near-term close.",
                    "weighted_pipeline_share", coverage, "weighted forecast / total pipeline × 100", ["amount", "probability"],
                ))
        stage = pipeline.get("stage_breakdown") or []
        if stage:
            lead = stage[0]
            amount = float(lead.get("amount") or 0)
            opportunities.append(_insight(
                "pipeline-stage", "info", f"{lead.get('stage')} holds the largest open stage value",
                f"Open value is {_money(amount)}.",
                "The largest open stage is a natural focus area for deal progression and inspection.",
                f"Review the opportunities in {lead.get('stage')} and identify the next concrete close step.",
                "stage_pipeline_value", amount, "sum(open opportunity amount) by stage", ["stage", "amount"],
            ))

    elif primary == "subscription":
        subscription = analyze_subscription_business(canonical)
        sm = subscription.get("metrics", {})
        mrr, arr, churn = sm.get("mrr"), sm.get("annualized_revenue"), sm.get("churn_rate_pct")
        metrics = [
            _metric("mrr", "MRR", mrr, _money(mrr), "sum(MRR)", ["mrr"]),
            _metric("arr", "ARR", arr, _money(arr), "MRR × 12", ["mrr"]),
            _metric("churn", "Churn", churn, _pct(churn), "churned records / snapshot records × 100", ["churn_status"], tone="risk" if churn is not None and churn >= 10 else "neutral"),
        ]
        if sm.get("snapshot_label"):
            what_changed.append(f"Current recurring-revenue view uses the latest available subscription snapshot ({sm['snapshot_label']}).")
        if churn is not None and churn >= 10:
            attention.append(_insight(
                "churn-risk", "high", f"Churn is {churn:.1f}%",
                "Churn is elevated in the latest available subscription snapshot.",
                "Customer losses directly threaten recurring revenue and retention.",
                "Review churned customers and plans to identify the highest-value retention opportunities.",
                "churn", churn, "churned records / snapshot records × 100", ["churn_status"],
            ))
        customers = subscription.get("customer_breakdown") or []
        if customers:
            lead = customers[0]
            customer_mrr = float(lead.get("mrr") or 0)
            opportunities.append(_insight(
                "top-mrr-customer", "info", f"{lead.get('customer')} has the highest MRR",
                f"Current MRR is {_money(customer_mrr)}.",
                "High-value accounts are good candidates for retention and expansion review.",
                f"Review {lead.get('customer')}'s plan, usage and renewal risk for expansion or retention opportunities.",
                "customer_mrr", customer_mrr, "sum(MRR) by customer", ["customer", "mrr"],
            ))

    elif primary == "services":
        services = analyze_services_business(canonical)
        sm = services.get("metrics", {})
        billings, hours, rate = sm.get("billings"), sm.get("hours"), sm.get("revenue_per_hour")
        metrics = [
            _metric("billings", "Billings", billings, _money(billings), "sum(billings)", ["billings"]),
            _metric("hours", "Hours", hours, _count(hours), "sum(hours)", ["hours"]),
            _metric("billing_per_hour", "Billing / hour", rate, _money(rate), "billings / hours", ["billings", "hours"]),
        ]
        clients = services.get("client_breakdown") or []
        if clients:
            lead = clients[0]
            client_billings = float(lead.get("revenue") or 0)
            opportunities.append(_insight(
                "top-client", "info", f"{lead.get('client')} is the leading client",
                f"Current billings are {_money(client_billings)}.",
                "The largest client can be a strong expansion target, but also merits concentration monitoring.",
                f"Review open work and upcoming services for {lead.get('client')} to identify expansion opportunities.",
                "client_billings", client_billings, "sum(billings) by client", ["client", "billings"],
            ))
        if hours == 0:
            attention.append(_insight(
                "zero-hours", "high", "No billable hours detected",
                "The dataset contains billings but no billable hours.",
                "Utilization and billing-per-hour analysis cannot be trusted without hours.",
                "Validate the hours field before using utilization or rate-based decisions.",
                "hours", hours, "sum(hours)", ["hours"],
            ))
        employees = services.get("employee_breakdown") or []
        if employees:
            lead = employees[0]
            what_changed.append(f"{lead.get('employee')} has the highest recorded hours at {_count(float(lead.get('hours') or 0))}.")

    current_scope_label = scope_label(scope) if scope is not None else "All data"
    for metric in metrics:
        metric.evidence.scope = current_scope_label
    for insight in [*attention, *opportunities]:
        insight.evidence.scope = current_scope_label

    headline = f"Your {summary.business_model_label or 'business'} at a glance"
    subheadline = f"{summary.file_name} · {summary.row_count:,} rows · {summary.column_count} fields · {summary.quality_issues} quality issues"
    return OverviewResponse(
        dataset_id=summary.dataset_id,
        scope_label=current_scope_label,
        business_model=summary.business_model,
        business_model_label=summary.business_model_label,
        headline=headline,
        subheadline=subheadline,
        metrics=metrics,
        what_changed=what_changed[:3],
        attention=attention[:3],
        opportunities=opportunities[:3],
    )
