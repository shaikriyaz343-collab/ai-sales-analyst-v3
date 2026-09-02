from __future__ import annotations

from types import SimpleNamespace

import pytest

import backend.api.runtime_persistence as runtime


class _Store:
    pass

@pytest.fixture(autouse=True)
def clean_runtime_registry():
    runtime.reset_runtime_persistence()
    yield
    runtime.reset_runtime_persistence()

def _context():
    return SimpleNamespace(
        mode="external",
        objects=_Store(),
        datasets=_Store(),
        sessions=_Store(),
        monitoring=_Store(),
        saved_intelligence=_Store(),
    )


def _settings(tmp_path):
    return SimpleNamespace(
        persistence_mode="external",
        runtime_root=tmp_path,
        database_url="postgresql://user:pass@example.com/app?sslmode=require",
        object_store_bucket="bucket",
        object_store_region="ap-south-1",
        object_store_endpoint_url=None,
        object_store_access_key=None,
        object_store_secret_key=None,
        object_store_prefix="v4",
        object_store_temp_root=tmp_path / "cache",
    )


def test_external_context_is_created_once(monkeypatch, tmp_path):
    calls = []
    context = _context()
    monkeypatch.setattr(runtime, "settings", _settings(tmp_path))
    monkeypatch.setattr(
        runtime,
        "build_persistence",
        lambda **kwargs: calls.append(kwargs) or context,
    )
    runtime.reset_runtime_persistence()

    assert runtime.get_runtime_persistence() is context
    assert runtime.get_runtime_persistence() is context
    assert len(calls) == 1


def test_external_namespaces_return_configured_stores(monkeypatch, tmp_path):
    context = _context()
    monkeypatch.setattr(runtime, "settings", _settings(tmp_path))
    monkeypatch.setattr(runtime, "build_persistence", lambda **_: context)
    runtime.reset_runtime_persistence()

    assert runtime.runtime_document_store("datasets", local_root=tmp_path) is context.datasets
    assert runtime.runtime_document_store("sessions", local_root=tmp_path) is context.sessions
    assert runtime.runtime_document_store("monitoring", local_root=tmp_path) is context.monitoring
    assert runtime.runtime_document_store("saved_intelligence", local_root=tmp_path) is context.saved_intelligence
    assert runtime.runtime_object_store(local_root=tmp_path) is context.objects


def test_local_mode_preserves_service_roots(monkeypatch, tmp_path):
    local_settings = _settings(tmp_path)
    local_settings.persistence_mode = "local"
    local_settings.database_url = None
    local_settings.object_store_bucket = None
    local_settings.object_store_region = None
    monkeypatch.setattr(runtime, "settings", local_settings)
    monkeypatch.setattr(
        runtime,
        "build_persistence",
        lambda **_: SimpleNamespace(
            mode="local",
            objects=None,
            datasets=None,
            sessions=None,
            monitoring=None,
            saved_intelligence=None,
        ),
    )
    runtime.reset_runtime_persistence()

    document_store = runtime.runtime_document_store("datasets", local_root=tmp_path / "docs")
    object_store = runtime.runtime_object_store(local_root=tmp_path / "objects")

    assert document_store.root == (tmp_path / "docs").resolve()
    assert object_store.root == (tmp_path / "objects").resolve()


def test_unknown_external_namespace_fails_closed(monkeypatch, tmp_path):
    context = _context()
    monkeypatch.setattr(runtime, "settings", _settings(tmp_path))
    monkeypatch.setattr(runtime, "build_persistence", lambda **_: context)
    runtime.reset_runtime_persistence()

    with pytest.raises(ValueError, match="Unsupported runtime document namespace"):
        runtime.runtime_document_store("unknown", local_root=tmp_path)
