from __future__ import annotations

from pathlib import Path

from business_analysis_packs_v1 import analyze_sales_forecast
from business_type_detector_v1 import detect_business_type
from schema_profiler_v2 import load_dataframe, normalize_column_name, profile_dataframe
from semantic_business_model_v2 import build_semantic_model

from ..contracts import Evidence, ForecastMonthly, ForecastResponse
from .onboarding import STORAGE, get_dataset
from .session import apply_scope, scope_label


def _actual_column(data, *aliases: str) -> str | None:
    wanted = {normalize_column_name(alias) for alias in aliases}
    return next((str(column) for column in data.columns if normalize_column_name(column) in wanted), None)


def build_forecast(dataset_id: str, scope=None) -> ForecastResponse:
    summary = get_dataset(dataset_id)
    if summary is None:
        raise ValueError("Dataset not found.")
    suffix = Path(summary.file_name).suffix.lower()
    path = STORAGE / f"{dataset_id}{suffix}"
    if not path.exists():
        raise ValueError("Dataset file is no longer available for analysis.")

    data = load_dataframe(path)
    profile = profile_dataframe(data)
    semantic = build_semantic_model(profile, data=data)
    business = detect_business_type(semantic, profile)
    primary = business.get("primary_type")
    if primary != "sales_pipeline":
        raise ValueError("Forecast is currently available for validated sales-pipeline datasets only.")

    if scope is not None:
        data = apply_scope(data, scope)

    result = analyze_sales_forecast(data)
    if not result.get("available"):
        raise ValueError("No validated forecast basis is available for this dataset.")

    probability_available = bool(result["metrics"].get("has_probability"))
    note = "Weighted forecast uses the validated probability field on open opportunities." if probability_available else str(result["notes"][0])
    close_col = _actual_column(data, "expected_close", "expected close", "expected close date", "close date")
    amount_col = _actual_column(data, "amount", "deal amount", "opportunity amount", "pipeline amount", "revenue")
    probability_col = _actual_column(data, "probability", "win probability", "close probability")
    stage_col = _actual_column(data, "stage", "opportunity stage", "deal stage")
    source_fields = [field for field in (close_col, amount_col, probability_col, stage_col) if field]

    weighted_value = float(result["metrics"]["weighted_forecast"])
    open_value = float(result["metrics"]["open_pipeline_value"])
    evidence = Evidence(
        metric="weighted_forecast",
        value=weighted_value,
        calculation="Sum of open opportunity amount × validated win probability; probabilities are normalized to 0–1 when supplied as percentages.",
        scope=scope_label(scope) if scope is not None else "All data",
        source_fields=source_fields,
    )

    monthly = [
        ForecastMonthly(
            month=str(item["month"]),
            expected_value=float(item["expected_value"]),
            weighted_forecast=float(item["weighted_forecast"]),
            opportunities=int(item["opportunities"]),
            evidence=Evidence(
                metric="weighted_forecast",
                value=float(item["weighted_forecast"]),
                calculation=f"Open opportunity amount × validated probability for {item['month']}.",
                scope=scope_label(scope) if scope is not None else "All data",
                source_fields=source_fields,
            ),
        )
        for item in result["monthly_forecast"]
    ]

    return ForecastResponse(
        dataset_id=summary.dataset_id,
        business_model=summary.business_model,
        business_model_label=summary.business_model_label,
        scope_label=scope_label(scope) if scope is not None else "All data",
        weighted_forecast=weighted_value,
        open_pipeline_value=open_value,
        open_opportunities=int(result["metrics"]["open_opportunities"]),
        has_probability=probability_available,
        basis_note=note,
        evidence=evidence,
        monthly_forecast=monthly,
    )
