import os
import io
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
from backend.api.persistence import S3ObjectStore, LocalObjectStore
from backend.api.services.onboarding import BoundedStream

@pytest.fixture
def efficient_harness(tmp_path):
    test_settings = replace(
        settings,
        persistence_mode="external",
        object_store_bucket="test-bucket",
        object_store_region="test-region",
        object_store_temp_root=tmp_path / "objects",
        runtime_root=tmp_path / "runtime",
        data_storage=tmp_path / "runtime" / "runtime_data",
        auth_storage=tmp_path / "runtime" / "runtime_saas",
    )
    (tmp_path / "objects").mkdir(parents=True, exist_ok=True)

    mock_s3 = MagicMock()
    store = S3ObjectStore("test-bucket", "test-region", temp_root=tmp_path / "objects", client=mock_s3)

    return test_settings, mock_s3, store

def test_external_upload_does_not_call_download_file(efficient_harness):
    test_settings, mock_s3, store = efficient_harness
    content = b"amount,stage\n100,Closed\n"
    stream = io.BytesIO(content)

    # upload
    cache_path = store.put_stream("data.csv", stream)

    # Check upload_file was called
    mock_s3.upload_file.assert_called_once()

    # Check download_file was NOT called
    mock_s3.download_file.assert_not_called()

    # Check exact bytes
    assert cache_path.exists()
    assert cache_path.read_bytes() == content

    # Check temps are cleaned up
    tmps = list(test_settings.object_store_temp_root.glob("*.tmp"))
    assert len(tmps) == 0

def test_oversized_upload_never_starts_s3_upload(efficient_harness):
    test_settings, mock_s3, store = efficient_harness
    content = b"a" * 1024
    stream = BoundedStream(io.BytesIO(content), max_bytes=512)

    with pytest.raises(ValueError, match="exceeds maximum allowed upload size"):
        store.put_stream("data.csv", stream)

    mock_s3.upload_file.assert_not_called()

    cache_path = store._cache_path("data.csv")
    assert not cache_path.exists()

    tmps = list(test_settings.object_store_temp_root.glob("*.tmp"))
    assert len(tmps) == 0

def test_s3_upload_failure_cleans_staging(efficient_harness):
    test_settings, mock_s3, store = efficient_harness
    content = b"amount,stage\n100,Closed\n"
    stream = io.BytesIO(content)

    mock_s3.upload_file.side_effect = botocore.exceptions.EndpointConnectionError(endpoint_url="fake")

    with pytest.raises(botocore.exceptions.EndpointConnectionError):
        store.put_stream("data.csv", stream)

    cache_path = store._cache_path("data.csv")
    assert not cache_path.exists()

    tmps = list(test_settings.object_store_temp_root.glob("*.tmp"))
    assert len(tmps) == 0

def test_profile_reads_exact_uploaded_bytes(efficient_harness):
    test_settings, mock_s3, store = efficient_harness
    content = b"unique_content_123"
    stream = io.BytesIO(content)

    def verify_upload(Filename, Bucket, Key):
        assert Path(Filename).read_bytes() == content

    mock_s3.upload_file.side_effect = verify_upload

    cache_path = store.put_stream("data.csv", stream)

    mock_s3.upload_file.assert_called_once()
    assert cache_path.read_bytes() == content

def test_local_object_store_regression(tmp_path):
    store = LocalObjectStore(root=tmp_path / "local_objects")
    content = b"local_content"
    stream = io.BytesIO(content)

    cache_path = store.put_stream("data.csv", stream)
    assert cache_path.exists()
    assert cache_path.read_bytes() == content

def test_upload_then_path_for_does_not_redownload(efficient_harness):
    test_settings, mock_s3, store = efficient_harness
    content = b"test"
    stream = io.BytesIO(content)

    store.put_stream("data.csv", stream)
    mock_s3.upload_file.assert_called_once()

    # Reset mock to prove download_file is not called when we request path_for
    mock_s3.reset_mock()

    cache_path = store.path_for("data.csv")
    assert cache_path.read_bytes() == content
    mock_s3.download_file.assert_not_called()
