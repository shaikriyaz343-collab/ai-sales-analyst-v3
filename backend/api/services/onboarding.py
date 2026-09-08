from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import BinaryIO, Any

from business_type_detector_v1 import detect_business_type
from data_quality_engine_v1 import run_data_quality_checks
from schema_profiler_v2 import profile_dataframe
from semantic_business_model_v2 import build_semantic_model

from ..config import settings
from ..contracts import DatasetSummary, SemanticSummary
from ..runtime_persistence import runtime_object_store, runtime_document_store


SUPPORTED = {".csv", ".xlsx", ".xls"}
STORAGE = settings.data_storage
WORKSPACES = ["overview", "explore", "insights", "ask", "actions", "reports", "monitoring", "saved"]


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


class BoundedStream:
    def __init__(self, stream: BinaryIO, max_bytes: int):
        self._stream = stream
        self._max_bytes = max_bytes
        self._bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        remaining_allowed = self._max_bytes - self._bytes_read
        if remaining_allowed < 0:
            raise ValueError("File exceeds maximum allowed upload size.")

        if size == -1 or size > remaining_allowed:
            safe_size = remaining_allowed + 1
        else:
            safe_size = size

        chunk = self._stream.read(safe_size)
        if chunk:
            self._bytes_read += len(chunk)
            if self._bytes_read > self._max_bytes:
                raise ValueError("File exceeds maximum allowed upload size.")
        return chunk

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

def _save_upload(file_name: str, stream: BinaryIO, dataset_id: str) -> Path:
    suffix = Path(file_name).suffix.lower()
    bounded = BoundedStream(stream, settings.upload_max_bytes)
    return runtime_object_store(local_root=STORAGE).put_stream(f"{dataset_id}{suffix}", bounded)


def _profile(file_path: Path, file_name: str, dataset_id: str, organization_id: str | None = None, workspace_id: str | None = None) -> DatasetSummary:
    profile = profile_dataframe(file_path)
    from schema_profiler_v2 import load_dataframe

    data = load_dataframe(file_path)
    semantic = build_semantic_model(profile, data=data)
    quality = run_data_quality_checks(data, semantic)
    business_type = detect_business_type(semantic, profile)

    summary = DatasetSummary(
        dataset_id=dataset_id,
        organization_id=organization_id,
        workspace_id=workspace_id,
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

    runtime_document_store("datasets", local_root=STORAGE).write(dataset_id, summary.model_dump())
    return summary


def onboard(file_name: str, stream: BinaryIO, organization_id: str | None = None, workspace_id: str | None = None) -> DatasetSummary:
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError("Supported files are CSV, XLSX, and XLS.")

    dataset_id = uuid.uuid4().hex
    try:
        path = _save_upload(file_name, stream, dataset_id)
        return _profile(path, file_name, dataset_id, organization_id=organization_id, workspace_id=workspace_id)
    except Exception:
        runtime_object_store(local_root=STORAGE).delete(f"{dataset_id}{suffix}")
        runtime_document_store("datasets", local_root=STORAGE).delete(dataset_id)
        raise


def get_dataset(dataset_id: str, organization_id: str | None = None, workspace_id: str | None = None) -> DatasetSummary | None:
    raw = runtime_document_store("datasets", local_root=STORAGE).read(dataset_id)
    if raw is None:
        return None
    summary = DatasetSummary.model_validate(raw)
    if organization_id is not None and summary.organization_id != organization_id:
        return None
    if workspace_id is not None and summary.workspace_id != workspace_id:
        return None
    return summary
