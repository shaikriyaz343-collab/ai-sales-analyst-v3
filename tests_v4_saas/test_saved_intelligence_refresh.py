from io import BytesIO
from pathlib import Path

from backend.api.services.onboarding import STORAGE, onboard
from backend.api.services.saved_intelligence import list_saved, save_intelligence
from backend.api.services.session import create_session

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_saved_explore_refresh_recalculates_current_dataset_and_evidence():
    summary = onboard("retail.csv", BytesIO((SAMPLES / "retail.csv").read_bytes()))
    session = create_session(summary.dataset_id)
    saved = save_intelligence(
        summary.dataset_id,
        session.session_id,
        {
            "name": "Revenue by product watch",
            "source_workspace": "explore",
            "source_id": "revenue:product",
            "metric": "revenue",
            "dimension": "product",
        },
    )
    baseline = list_saved(summary.dataset_id, session.session_id)
    item = next(x for x in baseline.items if x.id == saved.id)
    baseline_value = item.value
    assert baseline_value is not None
    assert item.evidence.source_records

    dataset_path = STORAGE / f"{summary.dataset_id}.csv"
    original = dataset_path.read_text(encoding="utf-8")
    try:
        dataset_path.write_text(
            original.rstrip("\n") + "\n9999,2026-01-15,Expansion,Expansion,Phone,1000,0,No Return\n",
            encoding="utf-8",
        )
        refreshed = list_saved(summary.dataset_id, session.session_id)
        updated = next(x for x in refreshed.items if x.id == saved.id)
        assert updated.value is not None
        assert updated.value > baseline_value
        assert updated.evidence.source_records
    finally:
        dataset_path.write_text(original, encoding="utf-8")
