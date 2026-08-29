from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import BinaryIO

from business_type_detector_v1 import detect_business_type
from data_quality_engine_v1 import run_data_quality_checks
from schema_profiler_v2 import profile_dataframe
from semantic_business_model_v2 import build_semantic_model

from ..contracts import DatasetSummary, SemanticSummary


SUPPORTED = {".csv", ".xlsx", ".xls"}
STORAGE = Path(__file__).resolve().parents[2] / "runtime_data"
WORKSPACES = ["overview", "explore", "insights", "ask", "actions", "reports", "monitoring"]


def _capabilities(semantic: dict | None = None, business_type: dict | None = None) -> dict:
    """Separate stable product workspaces from validated analytical concepts."""
    semantic = semantic or {}
    business_type = business_type or {}
    modules = sorted({str(x) for x in business_type.get("suggested_modules", [])})
    analytics = sorted({str(x) for x in semantic.get("available_concepts", [])})
    return {"workspaces": WORKSPACES.copy(), "analytics": analytics, "modules": modules}


def _semantic_summary(profile: dict, semantic: dict, data) -> SemanticSummary:
    concepts = sorted({str(x) for x in semantic.get("available_concepts", [])})
    fields = [str(x) for x in data.columns]

    # These are conservative classifications from the validated semantic concepts.
    # The full metric registry will own richer metric/dimension definitions later.
    metric_concepts = {
        "revenue", "quantity", "aov", "price", "discount_pct", "amount",
        "probability", "mrr", "arr", "billings", "hours", "utilization",
        "churn_rate", "weighted_pipeline", "pipeline",
    }
    metrics = sorted(c for c in concepts if c in metric_concepts)
    dimensions = sorted(c for c in concepts if c not in metric_concepts)
    return SemanticSummary(fields=fields, concepts=concepts, metrics=metrics, dimensions=dimensions)


def _save_upload(file_name: str, stream: BinaryIO, dataset_id: str) -> Path:
    STORAGE.mkdir(parents=True, exist_ok=True)
    suffix = Path(file_name).suffix.lower()
    target = STORAGE / f"{dataset_id}{suffix}"
    with target.open("wb") as handle:
        while chunk := stream.read(1024 * 1024):
            handle.write(chunk)
    return target


def _profile(file_path: Path, file_name: str, dataset_id: str) -> DatasetSummary:
    profile = profile_dataframe(file_path)
    from schema_profiler_v2 import load_dataframe

    data = load_dataframe(file_path)
    semantic = build_semantic_model(profile, data=data)
    quality = run_data_quality_checks(data, semantic)
    business_type = detect_business_type(semantic, profile)

    summary = DatasetSummary(
        dataset_id=dataset_id,
        file_name=file_name,
        file_type=file_path.suffix.lower().lstrip("."),
        row_count=int(len(data)),
        column_count=int(len(data.columns)),
        columns=[str(x) for x in data.columns],
        business_model=business_type.get("primary_type"),
        business_model_label=business_type.get("primary_label"),
        business_model_confidence=float(business_type.get("confidence") or 0.0),
        quality_issues=len(quality.get("issues", [])),
        semantic=_semantic_summary(profile, semantic, data),
        capabilities=_capabilities(semantic, business_type),
        supported_concepts=sorted(semantic.get("available_concepts", [])),
    )

    meta = STORAGE / f"{dataset_id}.json"
    meta.write_text(json.dumps(summary.model_dump(), indent=2), encoding="utf-8")
    return summary


def onboard(file_name: str, stream: BinaryIO) -> DatasetSummary:
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError("Supported files are CSV, XLSX, and XLS.")

    dataset_id = uuid.uuid4().hex
    path = _save_upload(file_name, stream, dataset_id)
    try:
        return _profile(path, file_name, dataset_id)
    except Exception:
        path.unlink(missing_ok=True)
        (STORAGE / f"{dataset_id}.json").unlink(missing_ok=True)
        raise


def get_dataset(dataset_id: str) -> DatasetSummary | None:
    meta = STORAGE / f"{dataset_id}.json"
    if not meta.exists():
        return None
    return DatasetSummary.model_validate(json.loads(meta.read_text(encoding="utf-8")))
