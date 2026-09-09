import os
import io
import time
import pytest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import botocore.exceptions

from backend.api.main import app, COOKIE_NAME
from backend.api.config import settings
import backend.api.runtime_persistence as runtime_persistence
import backend.api.services.auth as auth
from backend.api.persistence import S3ObjectStore

@pytest.fixture
def lifecycle_harness(tmp_path, monkeypatch):
    test_settings = replace(
        settings,
        persistence_mode="external",
        object_store_bucket="test-bucket",
        object_store_region="test-region",
        object_store_temp_root=tmp_path / "objects",
        runtime_root=tmp_path / "runtime",
        data_storage=tmp_path / "runtime" / "runtime_data",
        auth_storage=tmp_path / "runtime" / "runtime_saas",
        cache_max_bytes=100  # Cap at 100 bytes for testing
    )
    (tmp_path / "objects").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("backend.api.config.settings", test_settings)
    monkeypatch.setattr(runtime_persistence, "settings", test_settings)
    monkeypatch.setattr(auth, "settings", test_settings)

    mock_s3 = MagicMock()

    # We create the store inside a function so we can recreate it for startup tests
    def build_store():
        return S3ObjectStore("test-bucket", "test-region", temp_root=tmp_path / "objects", client=mock_s3)

    store = build_store()

    def mock_runtime_object_store(*, local_root):
        return store

    monkeypatch.setattr(runtime_persistence, "runtime_object_store", mock_runtime_object_store)

    return test_settings, mock_s3, store, build_store

def test_cache_below_cap_nothing_deleted(lifecycle_harness):
    test_settings, mock_s3, store, _ = lifecycle_harness
    cache_path = store._cache_path("small.csv")
    cache_path.write_bytes(b"A" * 50)

    store._evict_if_needed()
    assert cache_path.exists()

def test_cache_above_cap_oldest_evicted(lifecycle_harness):
    test_settings, mock_s3, store, _ = lifecycle_harness

    old_cache = store._cache_path("old.csv")
    new_cache = store._cache_path("new.csv")

    old_cache.write_bytes(b"A" * 60)
    os.utime(old_cache, (1000, 1000))

    new_cache.write_bytes(b"B" * 60)
    os.utime(new_cache, (2000, 2000))

    # Total is 120 > 100. Oldest should be evicted.
    store._evict_if_needed()

    assert not old_cache.exists()
    assert new_cache.exists()

def test_recency_changes_when_cache_is_used(lifecycle_harness):
    test_settings, mock_s3, store, _ = lifecycle_harness
    cache_path = store._cache_path("test.csv")
    cache_path.write_bytes(b"A" * 50)
    os.utime(cache_path, (1000, 1000))

    # path_for should trigger a recency update
    store.path_for("test.csv")

    assert cache_path.stat().st_mtime > 1000

def test_failed_eviction_missing_file_harmless(lifecycle_harness, monkeypatch):
    test_settings, mock_s3, store, _ = lifecycle_harness
    cache_path = store._cache_path("test.csv")
    cache_path.write_bytes(b"A" * 150)

    original_unlink = Path.unlink
    def mock_unlink(self, *args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    # Should not crash
    store._evict_if_needed()

def test_windows_sharing_violation_safely_skipped(lifecycle_harness, monkeypatch):
    test_settings, mock_s3, store, _ = lifecycle_harness

    old_cache = store._cache_path("old.csv")
    new_cache = store._cache_path("new.csv")

    old_cache.write_bytes(b"A" * 60)
    os.utime(old_cache, (1000, 1000))

    new_cache.write_bytes(b"B" * 60)
    os.utime(new_cache, (2000, 2000))

    # Mock unlink to throw a winerror 32 PermissionError on the OLD cache
    original_unlink = Path.unlink
    def mock_unlink(self, *args, **kwargs):
        if self == old_cache:
            exc = PermissionError("Sharing Violation")
            exc.winerror = 32
            raise exc
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    # Since old_cache is locked, it must be skipped, and new_cache should be evicted instead!
    store._evict_if_needed()

    assert old_cache.exists()  # Kept because of lock
    assert not new_cache.exists()  # Evicted to satisfy cap

def test_unrelated_permission_error_propagates(lifecycle_harness, monkeypatch):
    test_settings, mock_s3, store, _ = lifecycle_harness

    cache_path = store._cache_path("test.csv")
    cache_path.write_bytes(b"A" * 150)

    def mock_unlink(self, *args, **kwargs):
        exc = PermissionError("Access Denied")
        exc.winerror = 5
        raise exc

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    with pytest.raises(PermissionError, match="Access Denied"):
        store._evict_if_needed()

def test_orphaned_tmp_files_cleaned_on_startup(lifecycle_harness):
    test_settings, mock_s3, store, build_store = lifecycle_harness

    tmp_path = test_settings.object_store_temp_root / "orphan.tmp"
    tmp_path.write_bytes(b"A" * 10)

    valid_cache = store._cache_path("test.csv")
    valid_cache.write_bytes(b"A" * 10)

    # New store instance (simulating startup)
    new_store = build_store()

    assert not tmp_path.exists()
    assert valid_cache.exists()

def test_eviction_never_touches_s3(lifecycle_harness):
    test_settings, mock_s3, store, _ = lifecycle_harness
    cache_path = store._cache_path("test.csv")
    cache_path.write_bytes(b"A" * 150)

    store._evict_if_needed()

    assert not cache_path.exists()
    mock_s3.delete_object.assert_not_called()



def test_cache_byte_total_respects_cap(lifecycle_harness):
    test_settings, mock_s3, store, _ = lifecycle_harness

    # Cap is 100.
    c1 = store._cache_path("1.csv")
    c1.write_bytes(b"A" * 40)
    os.utime(c1, (1000, 1000))

    c2 = store._cache_path("2.csv")
    c2.write_bytes(b"A" * 40)
    os.utime(c2, (2000, 2000))

    c3 = store._cache_path("3.csv")
    c3.write_bytes(b"A" * 40)
    os.utime(c3, (3000, 3000))

    # Total is 120. Evict oldest (c1).
    store._evict_if_needed()

    assert not c1.exists()
    assert c2.exists()
    assert c3.exists()

def test_active_newer_cache_survives(lifecycle_harness):
    test_settings, mock_s3, store, _ = lifecycle_harness

    c1 = store._cache_path("1.csv")
    c1.write_bytes(b"A" * 80)
    os.utime(c1, (1000, 1000))

    c2 = store._cache_path("2.csv")
    c2.write_bytes(b"A" * 80)
    os.utime(c2, (2000, 2000))

    # 160 > 100. c1 is oldest, so c1 evicted.
    store._evict_if_needed()

    assert not c1.exists()
    assert c2.exists()
