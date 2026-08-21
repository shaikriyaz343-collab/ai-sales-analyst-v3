from __future__ import annotations

from typing import Any
import pandas as pd


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator in (0, None) or pd.isna(denominator):
        return None
    return float(numerator / denominator * 100)


def _fmt_currency(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "not available"
    return f"${value:,.2f}"


def _period_label(data: pd.DataFrame) -> str:
    if "date" not in data.columns or data.empty:
        return "the uploaded dataset"
    dates = pd.to_datetime(data["date"], errors="coerce").dropna()
    if dates.empty:
        return "the uploaded dataset"
    start, end = dates.min(), dates.max()
    if start.to_period("M") == end.to_period("M"):
        return start.strftime("%B %Y")
    return f"{start.strftime('%b %Y')}–{end.strftime('%b %Y')}"


def _dimension_concentration(
    data: pd.DataFrame,
    dimension: str,
    metric: str,
) -> dict[str, Any] | None:
    if dimension not in data.columns or metric not in data.columns:
        return None
    work = data[[dimension, metric]].copy()
    work[metric] = _num(work[metric])
    work = work.dropna(subset=[dimension, metric])
    if work.empty:
        return None
    grouped = (
        work.groupby(dimension)[metric]
        .sum()
        .sort_values(ascending=False)
    )
    total = float(grouped.sum())
    if total <= 0:
        return None
    name = str(grouped.index[0])
    value = float(grouped.iloc[0])
    return {
        "name": name,
        "value": value,
        "share_pct": float(value / total * 100),
        "total": total,
    }


def _monthly_change(data: pd.DataFrame, metric: str) -> dict[str, Any] | None:
    if "date" not in data.columns or metric not in data.columns:
        return None
    work = data[["date", metric]].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work[metric] = _num(work[metric])
    work = work.dropna(subset=["date", metric])
    if work.empty:
        return None
    monthly = work.assign(_period=work["date"].dt.to_period("M").astype(str)).groupby("_period")[metric].sum()
    if len(monthly) < 2:
        return None
    prev_period, curr_period = monthly.index[-2], monthly.index[-1]
    prev, curr = float(monthly.iloc[-2]), float(monthly.iloc[-1])
    pct = None if prev == 0 else (curr - prev) / abs(prev) * 100
    return {
        "previous_period": prev_period,
        "current_period": curr_period,
        "previous_value": prev,
        "current_value": curr,
        "change_pct": pct,
    }


def _latest_snapshot(data: pd.DataFrame, value_col: str) -> tuple[pd.DataFrame, str | None]:
    """Use the latest dated snapshot when dates repeat across a subscription file."""
    if "date" not in data.columns:
        return data.copy(), None
    work = data.copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    valid = work.dropna(subset=["date"])
    if valid.empty:
        return work, None
    latest = valid["date"].max()
    snapshot = valid[valid["date"] == latest].copy()
    return snapshot, latest.strftime("%B %d, %Y")


def build_business_brief(
    data: pd.DataFrame,
    profile: dict[str, Any],
    semantic_model: dict[str, Any],
    business_type: dict[str, Any],
    adaptive_analysis: dict[str, Any],
    packs: dict[str, Any],
    data_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create an evidence-first business brief shared by Overview, Attention, and Reports."""
    primary = business_type.get("primary_type")
    row_count = int(len(data))
    column_count = int(len(data.columns))
    period = _period_label(data)
    capabilities = semantic_model.get("capabilities", {})
    enabled = [k for k, v in capabilities.items() if v]

    # Capability count should reflect what the application can actually analyze,
    # not only semantic flags. This prevents states such as Services showing
    # "0 analysis capabilities" while Services/Billings/Utilization are live.
    adaptive_modules = adaptive_analysis.get(
        "enabled_modules",
        [],
    ) if isinstance(adaptive_analysis, dict) else []

    pack_modules = []
    for pack_name, pack in (
        packs.get("packs", {}).items()
        if isinstance(packs, dict)
        else []
    ):
        if isinstance(pack, dict) and pack.get("available"):
            pack_modules.append(pack_name)

    actual_capabilities = list(
        dict.fromkeys(
            list(enabled)
            + list(adaptive_modules)
            + list(pack_modules)
        )
    )

    brief: dict[str, Any] = {
        "business_type": primary,
        "period": period,
        "coverage": {
            "rows": row_count,
            "columns": column_count,
            "source_columns": int(profile.get("column_count", column_count)),
            "period": period,
            "coverage_label": "Limited" if row_count < 20 else "Moderate" if row_count < 100 else "Good",
            "schema_match": "Strong" if business_type.get("confidence", 0) >= 0.8 else "Moderate" if business_type.get("confidence", 0) >= 0.6 else "Needs review",
        },
        "capabilities": {
            "count": len(actual_capabilities),
            "labels": actual_capabilities,
            "dimensions": semantic_model.get("dimensions", []),
            "metrics": semantic_model.get("metrics", []),
        },
        "snapshot": [],
        "signals": [],
        "opportunities": [],
        "assumptions": [],
        "limitations": [],
    }

    if row_count < 20:
        brief["limitations"].append(
            "The uploaded dataset is small; findings should be treated as directional until more records are available."
        )
    if data_quality and data_quality.get("issue_count"):
        brief["limitations"].append(quality_summary_safe(data_quality))

    if primary == "transactional_sales":
        if "revenue" in data.columns:
            revenue = float(_num(data["revenue"]).sum())
            brief["snapshot"].append({"label": "Revenue", "value": _fmt_currency(revenue)})
        if "order_id" in data.columns:
            orders = int(data["order_id"].nunique())
            brief["snapshot"].append({"label": "Orders", "value": f"{orders:,}"})
        if "quantity" in data.columns:
            quantity = float(_num(data["quantity"]).sum())
            brief["snapshot"].append({"label": "Units", "value": f"{quantity:,.0f}"})
        if "revenue" in data.columns and "order_id" in data.columns:
            orders = data["order_id"].nunique()
            if orders:
                brief["snapshot"].append({"label": "AOV", "value": _fmt_currency(float(_num(data["revenue"]).sum()) / orders)})

        change = _monthly_change(data, "revenue")
        if change and change["change_pct"] is not None and abs(change["change_pct"]) >= 10:
            direction = "increased" if change["change_pct"] > 0 else "decreased"
            brief["signals"].append({
                "type": "trend",
                "priority": 85 if change["change_pct"] < 0 else 55,
                "title": f"Revenue {direction} {abs(change['change_pct']):.1f}%",
                "what_happened": f"Revenue moved from {_fmt_currency(change['previous_value'])} in {change['previous_period']} to {_fmt_currency(change['current_value'])} in {change['current_period']}.",
                "why_it_matters": "The latest period is materially different from the prior period and warrants a driver-level review.",
                "recommended_action": "Break the movement down by product and customer before deciding on corrective action.",
                "decision_question": "Which product or customer contributed most to this revenue change?",
            })

        for dim, label in [("product", "product"), ("customer", "customer")]:
            c = _dimension_concentration(data, dim, "revenue")
            if c and c["share_pct"] >= 50:
                brief["signals"].append({
                    "type": f"{dim}_concentration",
                    "priority": 82 if dim == "product" else 78,
                    "title": f"{label.title()} {c['name']} represents {c['share_pct']:.1f}% of revenue" + (" in the uploaded sample" if row_count < 20 else ""),
                    "what_happened": f"{label.title()} {c['name']} generated {_fmt_currency(c['value'])} out of {_fmt_currency(c['total'])} total revenue.",
                    "why_it_matters": (f"A large share of the recorded revenue depends on one {label}; the dataset is small, so treat this as directional." if row_count < 20 else f"A large share of the business depends on one {label}."),
                    "recommended_action": f"Review {label} {c['name']}'s trend, mix, and dependencies, and identify ways to diversify.",
                    "decision_question": f"Which periods and other dimensions are driving {label} {c['name']}'s revenue?",
                })

        if "return_status" in data.columns:
            returned = data["return_status"].astype(str).str.strip().str.lower().isin({"returned", "return", "yes", "y", "true", "refunded", "refund"})
            rate = float(returned.mean() * 100) if len(returned) else None
            if rate is not None and rate >= 5:
                brief["signals"].append({
                    "type": "returns",
                    "priority": 70,
                    "title": f"Return rate is {rate:.1f}%",
                    "what_happened": f"{rate:.1f}% of uploaded rows are marked as returned/refunded.",
                    "why_it_matters": "Returns can affect net sales, customer experience, and inventory planning.",
                    "recommended_action": "Compare returns by product and customer to identify concentrated return patterns.",
                    "decision_question": "Which products have the highest return rate?",
                })

        if "cost" in data.columns and "revenue" in data.columns:
            revenue = float(_num(data["revenue"]).sum())
            cost = float(_num(data["cost"]).sum())
            if revenue:
                margin = (revenue - cost) / revenue * 100
                brief["snapshot"].append({"label": "Gross margin", "value": f"{margin:.1f}%"})
        else:
            brief["limitations"].append("Profitability is not calculated because no cost field was found.")

    elif primary == "sales_pipeline":
        module = packs.get("packs", {}).get("sales_pipeline", {})
        forecast = packs.get("packs", {}).get("forecast", {})
        metrics = module.get("metrics", {}) if module else {}
        brief["snapshot"].extend([
            {"label": "Open pipeline", "value": _fmt_currency(metrics.get("open_pipeline_value", metrics.get("pipeline_value")))},
            {"label": "Opportunities", "value": f"{metrics.get('open_opportunities', metrics.get('opportunities', 0)):,}"},
            {"label": "Won value", "value": _fmt_currency(metrics.get("won_value"))},
            {"label": "Value win rate", "value": f"{metrics['win_rate_pct']:.1f}%" if metrics.get("win_rate_pct") is not None else "Not available"},
        ])
        lost, won = float(metrics.get("lost_value", 0) or 0), float(metrics.get("won_value", 0) or 0)
        if lost > won and lost > 0:
            brief["signals"].append({
                "type": "pipeline_loss",
                "priority": 86,
                "title": "Lost opportunity value exceeds won value",
                "what_happened": f"Lost opportunities totalled {_fmt_currency(lost)}, versus {_fmt_currency(won)} won.",
                "why_it_matters": "More value is leaving the closed pipeline than converting to won business.",
                "recommended_action": "Break lost value down by stage, salesperson, and loss reason to locate the conversion problem.",
                "decision_question": "Which sales stage accounts for the most lost value?",
            })
        if forecast and forecast.get("available"):
            fm = forecast.get("metrics", {})
            open_value = float(fm.get("open_pipeline_value", fm.get("pipeline_value", 0)) or 0)
            weighted = float(fm.get("weighted_forecast", 0) or 0)
            if open_value:
                coverage = weighted / open_value * 100
                brief["snapshot"].append({"label": "Weighted forecast", "value": _fmt_currency(weighted)})
                if coverage < 50:
                    brief["signals"].append({
                        "type": "forecast_uncertainty",
                        "priority": 74,
                        "title": f"Only {coverage:.1f}% of open pipeline is probability-weighted into forecast",
                        "what_happened": f"Weighted forecast is {_fmt_currency(weighted)} against {_fmt_currency(open_value)} of open pipeline.",
                        "why_it_matters": "A large part of the open pipeline has lower or missing probability support.",
                        "recommended_action": "Prioritize deals with credible close dates and stronger probability signals; review stale opportunities.",
                        "decision_question": "Which opportunities make up most of the weighted forecast?",
                    })
        reps = module.get("salesperson_breakdown", [])
        if reps:
            total = sum(float(r.get("amount", 0) or 0) for r in reps)
            if total:
                top = reps[0]
                share = float(top.get("amount", 0) or 0) / total * 100
                if share >= 50:
                    brief["signals"].append({
                        "type": "salesperson_concentration",
                        "priority": 60,
                        "title": f"{top.get('salesperson')} holds {share:.1f}% of listed pipeline value",
                        "what_happened": f"{top.get('salesperson')} has {_fmt_currency(float(top.get('amount',0) or 0))} of the listed pipeline.",
                        "why_it_matters": "A concentrated pipeline can create execution or coverage risk.",
                        "recommended_action": "Review deal ownership, stage mix, and coverage across the sales team.",
                        "decision_question": "Which reps own the most open pipeline and what stages are they in?",
                    })

    elif primary == "subscription":
        module = packs.get("packs", {}).get("subscription", {})
        metrics = module.get("metrics", {}) if module else {}
        brief["snapshot"].append({"label": "MRR", "value": _fmt_currency(metrics.get("mrr"))})
        brief["snapshot"].append({"label": "Annualized recurring revenue", "value": _fmt_currency(metrics.get("annualized_revenue"))})
        if metrics.get("churned_customer_rate_pct") is not None:
            brief["snapshot"].append({"label": "Customer churn rate", "value": f"{metrics['churned_customer_rate_pct']:.1f}%"})
        elif metrics.get("churn_rate_pct") is not None:
            brief["snapshot"].append({"label": "Record churn rate", "value": f"{metrics['churn_rate_pct']:.1f}%"})

        if metrics.get("snapshot_label"):
            brief["assumptions"].append(
                f"MRR is based on the latest dated subscription snapshot ({metrics['snapshot_label']})."
            )

        churn = metrics.get("churned_customer_rate_pct", metrics.get("churn_rate_pct"))
        if churn is not None and churn > 5:
            brief["signals"].append({
                "type": "churn",
                "priority": 88,
                "title": f"Customer churn rate is {churn:.1f}%",
                "what_happened": f"{churn:.1f}% of customers in the analyzed subscription scope are marked churned/cancelled.",
                "why_it_matters": "Churn directly reduces recurring revenue and increases renewal pressure.",
                "recommended_action": "Review churned accounts, plan mix, timing, and stated cancellation reasons before the next renewal cycle.",
                "decision_question": "Which customers churned and how much MRR did they represent?",
            })

        c = _dimension_concentration(
            module.get("_snapshot_data", data),
            "customer",
            "mrr",
        )
        if c and c["share_pct"] >= 50:
            brief["signals"].append({
                "type": "mrr_concentration",
                "priority": 78,
                "title": f"Customer {c['name']} represents {c['share_pct']:.1f}% of MRR",
                "what_happened": f"Customer {c['name']} contributes {_fmt_currency(c['value'])} of {_fmt_currency(c['total'])} MRR.",
                "why_it_matters": "Recurring revenue is heavily dependent on one customer.",
                "recommended_action": "Review renewal status and identify opportunities to diversify MRR across the customer base.",
                "decision_question": "Which plans and periods contribute most to this customer's MRR?",
            })

    elif primary == "services":
        module = packs.get("packs", {}).get("services", {})
        metrics = module.get("metrics", {}) if module else {}
        brief["snapshot"].extend([
            {"label": "Billings", "value": _fmt_currency(metrics.get("billings"))},
            {"label": "Hours", "value": f"{metrics.get('hours', 0):,.1f}"},
            {"label": "Revenue / hour", "value": _fmt_currency(metrics.get("revenue_per_hour"))},
        ])

        billing_metric = "billings" if "billings" in data.columns else "revenue"
        c = _dimension_concentration(data, "client", billing_metric) if "client" in data.columns else _dimension_concentration(data, "customer", billing_metric)
        if c and c["share_pct"] >= 50:
            brief["signals"].append({
                "type": "client_concentration",
                "priority": 80,
                "title": f"Client {c['name']} represents {c['share_pct']:.1f}% of billings",
                "what_happened": f"Client {c['name']} generated {_fmt_currency(c['value'])} of {_fmt_currency(c['total'])} recorded billings.",
                "why_it_matters": "A large share of billings depends on one client.",
                "recommended_action": "Review the client relationship and identify other accounts or services that can diversify billings.",
                "decision_question": f"Which services and periods generate the most billing from {c['name']}?",
            })
        if metrics.get("revenue_per_hour") is not None:
            brief["opportunities"].append({
                "title": "Billing productivity benchmark",
                "message": f"Recorded billing productivity is {_fmt_currency(metrics['revenue_per_hour'])} per hour. Compare this by client, service, and employee before changing rates or staffing.",
            })

    # Rank and keep a tight executive set.
    brief["signals"] = sorted(
        brief["signals"],
        key=lambda x: x.get("priority", 0),
        reverse=True,
    )[:5]

    if not brief["signals"]:
        brief["signals"].append({
            "type": "no_material_signal",
            "priority": 10,
            "title": "No material exception detected from the available fields",
            "what_happened": "The available metrics did not cross the current review thresholds.",
            "why_it_matters": "This does not prove that performance is healthy; it means the current automated checks did not flag a material exception.",
            "recommended_action": "Use the business-specific analysis and Ask Your Business Analyst to investigate the areas that matter most to you.",
            "decision_question": "What is the most important metric I should investigate next?",
        })

    return brief


def quality_summary_safe(data_quality: dict[str, Any]) -> str:
    issues = data_quality.get("issue_count", 0)
    return f"{issues} data-quality issue(s) were detected and should be reviewed before relying on the analysis."


def build_query_evidence(
    data: pd.DataFrame,
    question: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Return a user-facing evidence contract for a deterministic answer."""
    scope = plan.get("time_scope", {})
    if scope.get("type") == "month":
        month = scope.get("month")
        year = scope.get("year")
        scope_text = f"{pd.Timestamp(year=year or int(pd.to_datetime(data['date']).dt.year.max()), month=month, day=1):%B %Y}" if month else "Selected month"
    elif "date" in data.columns:
        dates = pd.to_datetime(data["date"], errors="coerce").dropna()
        scope_text = f"Full uploaded period ({dates.min():%b %Y}–{dates.max():%b %Y})" if not dates.empty else "Full uploaded dataset"
    else:
        scope_text = "Full uploaded dataset"

    metric = plan.get("metric", "revenue")
    entity = plan.get("entity", "business")
    operation = plan.get("operation", "lookup")
    formulas = {
        "revenue": "SUM(revenue)",
        "quantity": "SUM(quantity)",
        "orders": "COUNT DISTINCT(order_id)",
        "aov": "SUM(revenue) / COUNT DISTINCT(order_id)",
    }
    formula = formulas.get(metric, metric)

    source_fields = []
    if entity == "product" and "product" in data.columns:
        source_fields.append("product")
    if entity == "customer" and "customer" in data.columns:
        source_fields.append("customer")
    if metric == "revenue" and "revenue" in data.columns:
        source_fields.append("revenue")
    if metric == "quantity" and "quantity" in data.columns:
        source_fields.append("quantity")
    if metric in {"orders", "aov"} and "order_id" in data.columns:
        source_fields.append("order_id")
    if "date" in data.columns:
        source_fields.append("date")

    return {
        "question": question,
        "scope": scope_text,
        "operation": operation.replace("_", " "),
        "entity": entity,
        "metric": metric,
        "calculation": formula,
        "rows_in_file": int(len(data)),
        "source_fields": list(dict.fromkeys(source_fields)),
        "filters": {
            key: value
            for key, value in plan.get("filters", {}).items()
            if value
        },
        "limitations": [],
    }
