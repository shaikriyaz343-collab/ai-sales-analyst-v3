from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from business_type_detector_v1 import detect_business_type
from schema_profiler_v2 import load_dataframe, profile_dataframe
from semantic_business_model_v2 import build_semantic_model

from ..contracts import ExploreResponse, ExploreRow
from .onboarding import STORAGE, get_dataset
from .overview import _canonicalize


METRICS: dict[str, dict[str, dict[str, str]]] = {
    "transactional_sales": {
        "revenue": {"label": "Revenue", "kind": "money"},
        "quantity": {"label": "Quantity", "kind": "number"},
        "orders": {"label": "Orders", "kind": "number"},
        "aov": {"label": "Average Order Value", "kind": "money"},
        "return_rate": {"label": "Return Rate", "kind": "percent"},
    },
    "sales_pipeline": {
        "pipeline_value": {"label": "Pipeline", "kind": "money"},
        "weighted_pipeline": {"label": "Weighted Pipeline", "kind": "money"},
        "opportunities": {"label": "Opportunities", "kind": "number"},
        "win_rate": {"label": "Win Rate", "kind": "percent"},
    },
    "subscription": {
        "mrr": {"label": "MRR", "kind": "money"},
        "churn_rate": {"label": "Churn Rate", "kind": "percent"},
    },
    "services": {
        "billings": {"label": "Billings", "kind": "money"},
        "hours": {"label": "Hours", "kind": "number"},
        "billing_per_hour": {"label": "Billing per Hour", "kind": "money"},
    },
}

DIMENSIONS: dict[str, dict[str, str]] = {
    "transactional_sales": {
        "product": "Product",
        "customer": "Customer",
        "region": "Region",
        "payment_method": "Payment Method",
    },
    "sales_pipeline": {
        "stage": "Stage",
        "salesperson": "Salesperson",
        "customer": "Account",
    },
    "subscription": {
        "customer": "Customer",
        "plan": "Plan",
        "churn_status": "Churn Status",
    },
    "services": {
        "client": "Client",
        "service": "Service",
        "employee": "Employee",
    },
}

ADDITIVE_METRICS = {
    "revenue", "quantity", "orders", "pipeline_value", "weighted_pipeline",
    "opportunities", "mrr", "billings", "hours"
}


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def _format(kind: str, value: float | None) -> str:
    if value is None:
        return "—"
    if kind == "money":
        return _money(value)
    if kind == "percent":
        return f"{value:.1f}%"
    return f"{value:,.0f}"


def _canonical(data: pd.DataFrame, profile: dict[str, Any]) -> pd.DataFrame:
    return _canonicalize(data, profile)


def _metric_values(group: pd.DataFrame, metric: str) -> float | None:
    if metric == "revenue":
        return float(_num(group["revenue"]).sum()) if "revenue" in group else None
    if metric == "quantity":
        return float(_num(group["quantity"]).sum()) if "quantity" in group else None
    if metric == "orders":
        return float(group["order_id"].nunique()) if "order_id" in group else float(len(group))
    if metric == "aov":
        if "revenue" not in group:
            return None
        orders = group["order_id"].nunique() if "order_id" in group else len(group)
        return float(_num(group["revenue"]).sum() / orders) if orders else None
    if metric == "return_rate":
        if "return_status" not in group:
            return None
        orders = group["order_id"].nunique() if "order_id" in group else len(group)
        flags = group["return_status"].astype(str).str.strip().str.lower().isin(
            {"returned", "return", "yes", "y", "true", "1", "refunded", "refund"}
        )
        returned = group.loc[flags, "order_id"].nunique() if "order_id" in group else int(flags.sum())
        return float(returned / orders * 100) if orders else None
    if metric in {"pipeline_value", "weighted_pipeline", "opportunities", "win_rate"}:
        if "amount" not in group:
            return None
        amount = _num(group["amount"])
        if metric == "pipeline_value":
            return float(amount.sum())
        if metric == "weighted_pipeline":
            if "probability" not in group:
                return None
            prob = _num(group["probability"])
            if prob.max() > 1:
                prob = prob / 100.0
            prob = prob.clip(0, 1)
            return float((amount * prob).sum())
        if metric == "opportunities":
            key = group["opportunity_id"] if "opportunity_id" in group else group.index
            return float(pd.Series(key).nunique())
        stage_col = "stage" if "stage" in group else None
        if not stage_col:
            return None
        stage = group[stage_col].astype(str).str.lower().str.strip()
        won = stage.str.contains(r"won|closed won|success", regex=True)
        lost = stage.str.contains(r"lost|closed lost|failed", regex=True)
        denom = float(amount[won | lost].sum())
        return float(amount[won].sum() / denom * 100) if denom else None
    if metric == "mrr":
        return float(_num(group["mrr"]).sum()) if "mrr" in group else None
    if metric == "churn_rate":
        if "churn_status" not in group:
            return None
        status = group["churn_status"].astype(str).str.strip().str.lower()
        churned = status.str.contains(r"churn|cancel|inactive", regex=True)
        return float(churned.mean() * 100) if len(group) else None
    if metric == "billings":
        col = "billings" if "billings" in group else "revenue" if "revenue" in group else None
        return float(_num(group[col]).sum()) if col else None
    if metric == "hours":
        return float(_num(group["hours"]).sum()) if "hours" in group else None
    if metric == "billing_per_hour":
        billing_col = "billings" if "billings" in group else "revenue" if "revenue" in group else None
        if not billing_col or "hours" not in group:
            return None
        hours = float(_num(group["hours"]).sum())
        return float(_num(group[billing_col]).sum() / hours) if hours else None
    return None


def _source_fields(metric: str, dimension: str, data: pd.DataFrame) -> list[str]:
    mapping = {
        "revenue": ["revenue"], "quantity": ["quantity"], "orders": ["order_id"],
        "aov": ["revenue", "order_id"], "return_rate": ["return_status", "order_id"],
        "pipeline_value": ["amount"], "weighted_pipeline": ["amount", "probability"],
        "opportunities": ["opportunity_id"], "win_rate": ["amount", "stage"],
        "mrr": ["mrr"], "churn_rate": ["churn_status"],
        "billings": ["billings"], "hours": ["hours"], "billing_per_hour": ["billings", "hours"],
    }
    fields = [f for f in mapping.get(metric, []) if f in data.columns]
    if dimension in data.columns:
        fields.append(dimension)
    return fields


def build_explore(dataset_id: str, metric: str | None = None, dimension: str | None = None, limit: int = 8) -> ExploreResponse:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")
    suffix = Path(summary.file_name).suffix.lower()
    path = STORAGE / f"{dataset_id}{suffix}"
    if not path.exists():
        raise ValueError("Dataset file is no longer available for analysis.")

    data = load_dataframe(path)
    profile = profile_dataframe(path)
    semantic = build_semantic_model(profile, data=data)
    business = detect_business_type(semantic, profile)
    canonical = _canonical(data, profile)
    primary = business.get("primary_type")

    metric_defs = METRICS.get(primary, {})
    dim_defs = DIMENSIONS.get(primary, {})
    if not metric_defs or not dim_defs:
        raise ValueError("Explore is not available for this dataset.")
    metric = metric or next(iter(metric_defs))
    dimension = dimension or next((d for d in dim_defs if d in canonical.columns), None)
    if dimension is None:
        raise ValueError("No validated breakdown dimension is available for this dataset.")
    if metric not in metric_defs:
        raise ValueError(f"Metric '{metric}' is not supported for this dataset.")
    if dimension not in dim_defs:
        raise ValueError(f"Dimension '{dimension}' is not supported for this dataset.")
    if dimension not in canonical.columns:
        raise ValueError(f"Dimension '{dimension}' is not available in the validated dataset.")

    limit = max(3, min(int(limit), 15))
    total_value = _metric_values(canonical, metric)
    group_rows: list[tuple[str, pd.DataFrame]] = []
    for key, group in canonical.groupby(dimension, dropna=False, sort=False):
        label = "Unknown" if pd.isna(key) else str(key)
        group_rows.append((label, group))

    calculated = [(label, _metric_values(group, metric), group) for label, group in group_rows]
    calculated = [(label, value, group) for label, value, group in calculated if value is not None]
    calculated.sort(key=lambda item: item[1], reverse=True)
    shown = calculated[:limit]

    rows: list[ExploreRow] = []
    for label, value, group in shown:
        share = None
        if metric in ADDITIVE_METRICS and total_value not in (None, 0):
            share = float(value / total_value * 100)
        rows.append(
            ExploreRow(
                key=label,
                value=float(value),
                display_value=_format(metric_defs[metric]["kind"], value),
                share_pct=share,
                evidence={
                    "metric": metric,
                    "value": float(value),
                    "calculation": f"{metric_defs[metric]['label']} calculated for {dim_defs[dimension]} = {label}",
                    "scope": "All data",
                    "source_fields": _source_fields(metric, dimension, canonical),
                },
            )
        )

    return ExploreResponse(
        dataset_id=summary.dataset_id,
        business_model=summary.business_model,
        business_model_label=summary.business_model_label,
        metric=metric,
        metric_label=metric_defs[metric]["label"],
        dimension=dimension,
        dimension_label=dim_defs[dimension],
        total_value=total_value,
        total_display_value=_format(metric_defs[metric]["kind"], total_value),
        available_metrics=[{"id": k, "label": v["label"]} for k, v in metric_defs.items()],
        available_dimensions=[{"id": k, "label": v} for k, v in dim_defs.items() if k in canonical.columns],
        rows=rows,
    )
