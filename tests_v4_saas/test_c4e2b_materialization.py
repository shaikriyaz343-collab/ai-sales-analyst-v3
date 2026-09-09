import os
import io
import pytest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import botocore.exceptions
import concurrent.futures

from backend.api.main import app, COOKIE_NAME
from backend.api.config import settings
import backend.api.runtime_persistence as runtime_persistence
import backend.api.services.auth as auth

class FakeS3SlowDownload:
    def __init__(self, fail_download=False, slow=False):
        self.objects = {}
        self.fail_download = fail_download
        self.slow = slow
        self.outage = False

    def upload_fileobj(self, stream, bucket, key):
        if self.outage:
            raise botocore.exceptions.EndpointConnectionError(endpoint_url="fake")
        self.objects[(bucket, key)] = stream.read()

    def download_file(self, bucket, key, filepath):
        if self.outage:
            raise botocore.exceptions.EndpointConnectionError(endpoint_url="fake")
        if (bucket, key) not in self.objects:
            raise botocore.exceptions.ClientError({"Error": {"Code": "404"}}, "HeadObject")
        if self.fail_download:
            # Write partial file then crash
            Path(filepath).write_bytes(self.objects[(bucket, key)][:1])
            raise botocore.exceptions.EndpointConnectionError(endpoint_url="fake")

        if self.slow:
            import time
            time.sleep(0.5)

        Path(filepath).write_bytes(self.objects[(bucket, key)])

    def head_object(self, Bucket, Key):
        if self.outage:
            raise botocore.exceptions.EndpointConnectionError(endpoint_url="fake")
        if (Bucket, Key) not in self.objects:
            raise botocore.exceptions.ClientError({"Error": {"Code": "404"}}, "HeadObject")

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)


@pytest.fixture
def materialization_harness(tmp_path, monkeypatch):
    import backend.api.main as main_module
    import backend.api.services.auth_postgres as auth_postgres
    import backend.api.persistence as persistence

    # For these isolated unit-level concurrency tests, we use the local persistence
    # for Postgres tables so we don't need the rehearsal DB, but we configure S3ObjectStore
    # by directly overriding `runtime_object_store`.

    test_settings = replace(
        settings,
        persistence_mode="local",
        object_store_bucket="test-bucket",
        object_store_region="test-region",
        object_store_temp_root=tmp_path / "objects",
        runtime_root=tmp_path / "runtime",
        data_storage=tmp_path / "runtime" / "runtime_data",
        auth_storage=tmp_path / "runtime" / "runtime_saas",
    )

    (tmp_path / "objects").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(main_module, "settings", test_settings)
    monkeypatch.setattr(runtime_persistence, "settings", test_settings)
    monkeypatch.setattr(auth, "settings", test_settings)

    fake_s3 = FakeS3SlowDownload()
    store = persistence.S3ObjectStore("test-bucket", "test-region", temp_root=tmp_path / "objects", client=fake_s3)

    def mock_runtime_object_store(*, local_root):
        return store

    monkeypatch.setattr(runtime_persistence, "runtime_object_store", mock_runtime_object_store)

    runtime_persistence.reset_runtime_persistence()
    auth.reset_external_auth()

    yield test_settings, fake_s3, store


def test_successful_materialization(materialization_harness):
    test_settings, fake_s3, store = materialization_harness
    fake_s3.objects[("test-bucket", "test.csv")] = b"amount\\n100\\n"

    path = store.path_for("test.csv")
    assert path.exists()
    assert path.read_bytes() == b"amount\\n100\\n"

def test_failed_download_leaves_no_final_file(materialization_harness):
    test_settings, fake_s3, store = materialization_harness
    fake_s3.objects[("test-bucket", "test.csv")] = b"amount\\n100\\n"
    fake_s3.fail_download = True

    with pytest.raises(Exception):
        store.path_for("test.csv")

    # The final cache file should NOT exist
    cache_path = store._cache_path("test.csv")
    assert not cache_path.exists()

    # The temp file should be cleaned up
    tmps = list(test_settings.object_store_temp_root.glob("*.tmp"))
    assert len(tmps) == 0

def test_concurrent_cold_cache_requests_cannot_corrupt(materialization_harness):
    test_settings, fake_s3, store = materialization_harness
    fake_s3.objects[("test-bucket", "test.csv")] = b"amount\\n100\\n"
    fake_s3.slow = True

    def download():
        return store.path_for("test.csv")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(download) for _ in range(3)]
        results = [f.result() for f in futures]

    for path in results:
        assert path.exists()
        assert path.read_bytes() == b"amount\\n100\\n"

    # There should only be ONE final file in the directory
    files = list(test_settings.object_store_temp_root.glob("*.csv"))
    assert len(files) == 1

    # No tmp files
    tmps = list(test_settings.object_store_temp_root.glob("*.tmp"))
    assert len(tmps) == 0

def test_existing_valid_cache_never_replaced_by_failed_download(materialization_harness):
    test_settings, fake_s3, store = materialization_harness
    fake_s3.objects[("test-bucket", "test.csv")] = b"amount\\n100\\n"

    # 1. Successful download
    path = store.path_for("test.csv")
    assert path.exists()
    assert path.read_bytes() == b"amount\\n100\\n"

    # 2. Now S3 starts failing
    fake_s3.fail_download = True

    # 3. Requesting again should hit the valid cache and NOT fail, and NOT overwrite
    path2 = store.path_for("test.csv")
    assert path2.exists()
    assert path2.read_bytes() == b"amount\\n100\\n"



def test_simulated_concurrent_publication_wins(materialization_harness, monkeypatch):
    test_settings, fake_s3, store = materialization_harness
    fake_s3.objects[("test-bucket", "test.csv")] = b"amount\n100\n"

    cache = store._cache_path("test.csv")
    cache.write_bytes(b"amount\n100\n")

    original_exists = Path.exists
    call_count = 0
    def mock_exists(self):
        nonlocal call_count
        if self == cache:
            call_count += 1
            if call_count == 1:
                return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", mock_exists)

    def mock_replace(*args, **kwargs):
        exc = PermissionError("Access Denied")
        exc.winerror = 5
        raise exc

    monkeypatch.setattr(Path, "replace", mock_replace)

    path = store.path_for("test.csv")
    assert path == cache
    assert path.read_bytes() == b"amount\n100\n"

    tmps = list(test_settings.object_store_temp_root.glob("*.tmp"))
    assert len(tmps) == 0

def test_winerror_5_with_stale_cache_propagates(materialization_harness, monkeypatch):
    test_settings, fake_s3, store = materialization_harness
    fake_s3.objects[("test-bucket", "test.csv")] = b"amount\n100\n"

    cache = store._cache_path("test.csv")
    cache.write_bytes(b"amount\n100\nEXTRA") # DIFFERENT SIZE!

    original_exists = Path.exists
    call_count = 0
    def mock_exists(self):
        nonlocal call_count
        if self == cache:
            call_count += 1
            if call_count == 1: return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", mock_exists)

    def mock_replace(*args, **kwargs):
        exc = PermissionError("Access Denied")
        exc.winerror = 5
        raise exc

    monkeypatch.setattr(Path, "replace", mock_replace)

    with pytest.raises(PermissionError, match="Access Denied"):
        store.path_for("test.csv")

def test_genuine_permission_error_with_no_cache_propagates(materialization_harness, monkeypatch):
    test_settings, fake_s3, store = materialization_harness
    fake_s3.objects[("test-bucket", "test.csv")] = b"amount\n100\n"

    def mock_replace(*args, **kwargs):
        exc = PermissionError("Access Denied")
        exc.winerror = 5
        raise exc

    monkeypatch.setattr(Path, "replace", mock_replace)

    with pytest.raises(PermissionError, match="Access Denied"):
        store.path_for("test.csv")

    tmps = list(test_settings.object_store_temp_root.glob("*.tmp"))
    assert len(tmps) == 0
