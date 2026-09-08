import pytest
import io
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.config import settings
from backend.api.persistence import PersistenceConfigurationError, S3ObjectStore
import botocore.exceptions

@pytest.fixture(autouse=True)
def setup_env():
    # We need a mock user for authenticated routes
    from backend.api.services.auth import create_account, issue_session, principal_from_token

    # Ensure persistence works
    from backend.api.runtime_persistence import start_runtime_persistence, reset_runtime_persistence
    start_runtime_persistence()
    yield
    reset_runtime_persistence()

def _get_auth_client():
    from backend.api.services.auth import create_account, issue_session
    try:
        p = create_account("test@example.com", "password123", "Test", "Test Org")
    except ValueError:
        from backend.api.services.auth import authenticate
        p = authenticate("test@example.com", "password123")

    token, _ = issue_session(p.user_id)
    client = TestClient(app, raise_server_exceptions=False)
    from backend.api.main import COOKIE_NAME
    client.cookies.set(COOKIE_NAME, token)
    return client

def test_upload_just_under_limit():
    client = _get_auth_client()
    size = settings.upload_max_bytes - 1
    content = b"x" * size
    file_like = io.BytesIO(content)

    response = client.post("/api/v1/onboarding/profile", files={"file": ("test.csv", file_like, "text/csv")})
    # If it's valid CSV it's 200, if invalid 4xx, but not 400 size error.
    assert response.status_code in (200, 422)
    if response.status_code == 400:
        assert "exceeds maximum allowed" not in response.text

def test_upload_exactly_limit():
    client = _get_auth_client()
    size = settings.upload_max_bytes
    content = b"x" * size
    file_like = io.BytesIO(content)

    response = client.post("/api/v1/onboarding/profile", files={"file": ("test.csv", file_like, "text/csv")})
    assert response.status_code in (200, 422)
    if response.status_code == 400:
        assert "exceeds maximum allowed" not in response.text

def test_upload_over_limit():
    client = _get_auth_client()
    size = settings.upload_max_bytes + 1
    content = b"x" * size
    file_like = io.BytesIO(content)

    response = client.post("/api/v1/onboarding/profile", files={"file": ("test.csv", file_like, "text/csv")})
    # BoundedStream raises ValueError, caught in main.py as 400
    assert response.status_code == 400
    assert "File exceeds maximum allowed upload size." in response.text

def test_upload_failure_cleanup(tmp_path):
    client = _get_auth_client()
    size = settings.upload_max_bytes + 100
    content = b"x" * size
    file_like = io.BytesIO(content)

    with patch("backend.api.services.onboarding.STORAGE", tmp_path / "data"):
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        response = client.post("/api/v1/onboarding/profile", files={"file": ("test.csv", file_like, "text/csv")})
        assert response.status_code == 400

        # Ensure no partial files remain in storage
        files = list((tmp_path / "data").glob("*.*"))
        assert len(files) == 0

def test_error_safety_no_leakage():
    client = _get_auth_client()

    # Trigger an internal error using a mock
    with patch("backend.api.main._scope_for", return_value={}):
        with patch("backend.api.main.build_overview", side_effect=RuntimeError("Secret internal error details 12345")):
            response = client.get("/api/v1/datasets/fake-dataset-id/overview")

            # It should hit the global exception handler and return 500
            assert response.status_code == 500
            assert "Secret internal error details 12345" not in response.text
            assert "Internal Server Error" in response.text

def test_s3_missing_vs_outage():
    store = S3ObjectStore(bucket="test", region="us-east-1", client=MagicMock())

    # Missing object (404)
    missing_response = {"Error": {"Code": "404"}}
    store.client.head_object.side_effect = botocore.exceptions.ClientError(missing_response, "HeadObject")
    assert store.exists("some/key") is False

    # Outage / permission error (403)
    outage_response = {"Error": {"Code": "403"}}
    store.client.head_object.side_effect = botocore.exceptions.ClientError(outage_response, "HeadObject")
    with pytest.raises(PersistenceConfigurationError):
        store.exists("some/key")

    # Timeout/network error
    store.client.head_object.side_effect = botocore.exceptions.EndpointConnectionError(endpoint_url="http://test")
    with pytest.raises(PersistenceConfigurationError):
        store.exists("some/key")

def test_404_metric_cardinality():
    # If a user hits a fake URL, it should be unmatched_route
    client = TestClient(app, raise_server_exceptions=False)
    # Patch safe_emit_metric to inspect the label

    emitted = []
    def mock_emit(name, value, labels):
        emitted.append((name, labels))

    with patch("backend.api.telemetry.safe_emit_metric", side_effect=mock_emit):
        client.get("/api/v1/some-fake-url-with-pii/secret123")

        # Verify that unmatched_route is used
        for name, labels in emitted:
            if "route" in labels:
                assert labels["route"] == "unmatched_route"

from backend.api.services.onboarding import BoundedStream

def test_bounded_stream_read_all_limits_memory():
    # Prove read(-1) cannot load an oversized stream into memory
    class OversizedMockStream:
        def __init__(self):
            self.read_called_with = None
        def read(self, size):
            self.read_called_with = size
            return b"x" * size

    mock_stream = OversizedMockStream()
    bounded = BoundedStream(mock_stream, 10)

    import pytest
    with pytest.raises(ValueError, match="File exceeds maximum allowed upload size."):
        bounded.read(-1)

    # The underlying stream must only have been asked for 11 bytes, NOT -1 (everything)
    assert mock_stream.read_called_with == 11

def test_bounded_stream_arbitrary_large_read_limits_memory():
    # Prove arbitrary large read requests remain bounded
    class OversizedMockStream:
        def __init__(self):
            self.read_called_with = None
        def read(self, size):
            self.read_called_with = size
            return b"x" * size

    mock_stream = OversizedMockStream()
    bounded = BoundedStream(mock_stream, 10)

    import pytest
    with pytest.raises(ValueError, match="File exceeds maximum allowed upload size."):
        bounded.read(9999999)

    # The underlying stream must only have been asked for 11 bytes, NOT 9999999
    assert mock_stream.read_called_with == 11

def test_bounded_stream_exact_limit_eof_succeeds():
    # exactly limit with EOF succeeds
    import io
    stream = io.BytesIO(b"x" * 10)
    bounded = BoundedStream(stream, 10)

    # Read exactly 10
    data = bounded.read(10)
    assert len(data) == 10

    # Read again, hits EOF
    data2 = bounded.read(10)
    assert len(data2) == 0

def test_bounded_stream_exact_limit_plus_one_fails():
    # exact limit with one extra byte fails
    import io
    import pytest
    stream = io.BytesIO(b"x" * 11)
    bounded = BoundedStream(stream, 10)

    # Read exactly 10
    data = bounded.read(10)
    assert len(data) == 10

    # Read again, there is 1 more byte, which exceeds the limit
    with pytest.raises(ValueError, match="File exceeds maximum allowed upload size."):
        bounded.read(10)

def test_bounded_stream_repeated_reads():
    # repeated reads remain correct
    import io
    stream = io.BytesIO(b"x" * 10)
    bounded = BoundedStream(stream, 10)

    # Read in chunks of 3
    assert len(bounded.read(3)) == 3
    assert len(bounded.read(3)) == 3
    assert len(bounded.read(3)) == 3
    assert len(bounded.read(3)) == 1
    assert len(bounded.read(3)) == 0
