from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from backend.api.persistence import (
    LocalJsonDocumentStore,
    LocalObjectStore,
    PersistenceConfigurationError,
    build_local_persistence,
    build_persistence,
)


def test_local_persistence_context_separates_resource_domains(tmp_path: Path):
    context = build_local_persistence(tmp_path)
    assert context.mode == "local"
    assert context.datasets is not context.sessions
    assert context.monitoring is not context.saved_intelligence


def test_local_object_store_rejects_path_escape(tmp_path: Path):
    store = LocalObjectStore(tmp_path / "objects")
    with pytest.raises(ValueError, match="escapes"):
        store.path_for("../secret.txt")


def test_local_json_store_rejects_path_escape(tmp_path: Path):
    store = LocalJsonDocumentStore(tmp_path / "json")
    with pytest.raises(ValueError, match="escapes"):
        store.write("../secret", {"ok": False})


def test_local_persistence_round_trip(tmp_path: Path):
    context = build_local_persistence(tmp_path)
    context.datasets.write("dataset-1", {"organization_id": "org-1", "dataset_id": "dataset-1"})
    assert context.datasets.read("dataset-1")["organization_id"] == "org-1"

    path = context.objects.put_stream("dataset-1.csv", BytesIO(b"a,b\n1,2\n"))
    assert path.exists()
    assert context.objects.path_for("dataset-1.csv").read_bytes() == b"a,b\n1,2\n"


def test_external_persistence_requires_configuration(tmp_path: Path):
    with pytest.raises(PersistenceConfigurationError, match="External persistence requires"):
        build_persistence(mode="external", runtime_root=tmp_path)
