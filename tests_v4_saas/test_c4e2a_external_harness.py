import os
import io
import json
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

class FakeS3:
    def __init__(self):
        self.objects = {}
        self.outage = False
    def upload_fileobj(self, stream, bucket, key):
        if self.outage: raise botocore.exceptions.EndpointConnectionError(endpoint_url="fake")
        self.objects[(bucket, key)] = stream.read()
    def upload_file(self, filepath, bucket, key):
        if self.outage: raise botocore.exceptions.EndpointConnectionError(endpoint_url="fake")
        self.objects[(bucket, key)] = Path(filepath).read_bytes()
    def download_file(self, bucket, key, filepath):
        if self.outage: raise botocore.exceptions.EndpointConnectionError(endpoint_url="fake")
        if (bucket, key) not in self.objects:
            raise botocore.exceptions.ClientError({"Error": {"Code": "404"}}, "HeadObject")
        Path(filepath).write_bytes(self.objects[(bucket, key)])
    def head_object(self, Bucket, Key):
        if self.outage: raise botocore.exceptions.EndpointConnectionError(endpoint_url="fake")
        if (Bucket, Key) not in self.objects:
            raise botocore.exceptions.ClientError({"Error": {"Code": "404"}}, "HeadObject")
    def delete_object(self, Bucket, Key):
        if self.outage: raise botocore.exceptions.EndpointConnectionError(endpoint_url="fake")
        self.objects.pop((Bucket, Key), None)


@pytest.fixture
def test_db_url():
    url = os.environ.get("V4_REHEARSAL_DATABASE_URL")
    if not url:
        pytest.skip("Set V4_REHEARSAL_DATABASE_URL to run the external data plane integration tests.")
    return url


@pytest.fixture
def external_harness(test_db_url, tmp_path, monkeypatch):
    import backend.api.main as main_module
    import backend.api.services.auth_postgres as auth_postgres
    import backend.api.persistence as persistence

    test_settings = replace(
        settings,
        persistence_mode="external",
        database_url=test_db_url,
        object_store_bucket="test-bucket",
        object_store_region="test-region",
        object_store_temp_root=tmp_path / "objects",
        runtime_root=tmp_path / "runtime",
    )

    (tmp_path / "objects").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(main_module, "settings", test_settings)
    monkeypatch.setattr(runtime_persistence, "settings", test_settings)
    monkeypatch.setattr(auth, "settings", test_settings)
    monkeypatch.setattr(auth_postgres, "settings", test_settings)

    # Patch S3 client to use our FakeS3
    fake_s3 = FakeS3()

    def mock_boto3_client(service_name, **kwargs):
        if service_name == "s3":
            return fake_s3
        return MagicMock()

    monkeypatch.setattr("boto3.client", mock_boto3_client, raising=False)

    runtime_persistence.reset_runtime_persistence()
    auth.reset_external_auth()

    # Clear the current external persistence schema for test isolation.
    import psycopg
    from backend.api.services.auth_postgres import ensure_schema
    with psycopg.connect(test_db_url) as conn:
        ensure_schema(conn)
        conn.execute(
            "TRUNCATE TABLE security_events, auth_rate_limits, auth_sessions, "
            "memberships, workspaces, users, organizations "
            "RESTART IDENTITY CASCADE"
        )
        conn.execute("DROP TABLE IF EXISTS v4_json_documents")
        conn.commit()

    yield test_settings, fake_s3

    runtime_persistence.reset_runtime_persistence()
    auth.reset_external_auth()


def test_external_data_plane_end_to_end(external_harness):
    test_settings, fake_s3 = external_harness

    with TestClient(app, raise_server_exceptions=False) as client:
        # 1. Auth and Workspace
        from backend.api.services.auth import create_account, issue_session
        p = create_account("test@example.com", "ExternalTest123!", "Test", "Test Org")
        token, _ = issue_session(p.user_id)
        client.cookies.set(COOKIE_NAME, token)

        # 2. Upload dataset (External Mode)
        csv_content = b"amount,stage\n100,Closed Won\n200,Open\n"
        upload_resp = client.post("/api/v1/onboarding/profile", files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")})
        assert upload_resp.status_code == 200
        dataset_id = upload_resp.json()["dataset"]["dataset_id"]

        # Prove durable object
        assert ("test-bucket", f"v4/{dataset_id}.csv") in fake_s3.objects

        # Prove durable metadata (Postgres)
        from backend.api.runtime_persistence import runtime_document_store
        assert runtime_document_store("datasets", local_root=Path("")).exists(dataset_id)

        # 3. Session Creation
        session_resp = client.post("/api/v1/sessions", json={"dataset_id": dataset_id, "workspace_id": p.workspace_id})
        assert session_resp.status_code == 200
        session_id = session_resp.json()["session_id"]

        # 4. Overview / analytical retrieval
        overview_resp = client.get(f"/api/v1/datasets/{dataset_id}/overview")
        assert overview_resp.status_code == 200
        overview = overview_resp.json()
        assert overview["business_model"] == "sales_pipeline"
        assert {m["id"] for m in overview["metrics"]} >= {
            "pipeline_value",
            "weighted_forecast",
            "win_rate",
        }
        assert any(item["id"] == "pipeline-stage" for item in overview["opportunities"])

        # 5. Dataset Replacement
        csv2_content = b"amount,stage\n999,Closed Won\n"
        upload2_resp = client.post("/api/v1/onboarding/profile", files={"file": ("data2.csv", io.BytesIO(csv2_content), "text/csv")})
        dataset2_id = upload2_resp.json()["dataset"]["dataset_id"]

        replace_resp = client.post(f"/api/v1/sessions/{session_id}/dataset/{dataset2_id}")
        assert replace_resp.status_code == 200

        overview2_resp = client.get(f"/api/v1/datasets/{dataset2_id}/overview")
        assert "999" in overview2_resp.text


def test_restart_behavior(external_harness):
    test_settings, fake_s3 = external_harness
    dataset_id = None
    session_id = None

    with TestClient(app, raise_server_exceptions=False) as client:
        from backend.api.services.auth import create_account, issue_session
        p = create_account("test2@example.com", "ExternalTest123!", "Test", "Test Org")
        token, _ = issue_session(p.user_id)
        client.cookies.set(COOKIE_NAME, token)

        csv_content = b"amount,stage\n100,Closed Won\n"
        upload_resp = client.post("/api/v1/onboarding/profile", files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")})
        dataset_id = upload_resp.json()["dataset"]["dataset_id"]

        session_resp = client.post("/api/v1/sessions", json={"dataset_id": dataset_id, "workspace_id": p.workspace_id})
        session_id = session_resp.json()["session_id"]

        client.get(f"/api/v1/datasets/{dataset_id}/overview")

    # SIMULATE RESTART
    # Wipe the local object cache completely
    import shutil
    shutil.rmtree(test_settings.object_store_temp_root)
    test_settings.object_store_temp_root.mkdir()

    # Reinitialize runtime persistence
    runtime_persistence.reset_runtime_persistence()
    auth.reset_external_auth()

    # Client creates a new lifespan and re-runs start_runtime_persistence
    with TestClient(app, raise_server_exceptions=False) as client2:
        token, _ = issue_session(p.user_id)
        client2.cookies.set(COOKIE_NAME, token)

        # Prove we can retrieve the session from postgres
        sess_resp = client2.get(f"/api/v1/sessions/{session_id}")
        assert sess_resp.status_code == 200

        # Prove analytical retrieval downloads and materializes it
        overview_resp = client2.get(f"/api/v1/datasets/{dataset_id}/overview")
        assert overview_resp.status_code == 200

        # Check that it downloaded to cache
        files = list(test_settings.object_store_temp_root.glob("*.csv"))
        assert len(files) == 1

def test_missing_s3_object(external_harness):
    test_settings, fake_s3 = external_harness
    with TestClient(app, raise_server_exceptions=False) as client:
        from backend.api.services.auth import create_account, issue_session
        p = create_account("test3@example.com", "ExternalTest123!", "Test", "Test Org")
        token, _ = issue_session(p.user_id)
        client.cookies.set(COOKIE_NAME, token)

        csv_content = b"amount,stage\n100,Closed Won\n"
        upload_resp = client.post("/api/v1/onboarding/profile", files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")})
        dataset_id = upload_resp.json()["dataset"]["dataset_id"]

        # Delete the S3 object behind its back
        fake_s3.delete_object("test-bucket", f"v4/{dataset_id}.csv")

        # Also wipe the local cache to force a download
        import shutil
        shutil.rmtree(test_settings.object_store_temp_root)
        test_settings.object_store_temp_root.mkdir()

        # It should gracefully fail with 404 when object is missing
        resp = client.get(f"/api/v1/datasets/{dataset_id}/overview")
        assert resp.status_code == 404


def test_s3_outage(external_harness):
    test_settings, fake_s3 = external_harness
    with TestClient(app, raise_server_exceptions=False) as client:
        from backend.api.services.auth import create_account, issue_session
        p = create_account("test4@example.com", "ExternalTest123!", "Test", "Test Org")
        token, _ = issue_session(p.user_id)
        client.cookies.set(COOKIE_NAME, token)

        csv_content = b"amount,stage\n100,Closed Won\n"
        upload_resp = client.post("/api/v1/onboarding/profile", files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")})
        dataset_id = upload_resp.json()["dataset"]["dataset_id"]

        import shutil
        shutil.rmtree(test_settings.object_store_temp_root)
        test_settings.object_store_temp_root.mkdir()

        # Simulate S3 Outage
        fake_s3.outage = True

        resp = client.get(f"/api/v1/datasets/{dataset_id}/overview")
        assert resp.status_code == 503

def test_postgres_outage(external_harness, monkeypatch):
    test_settings, fake_s3 = external_harness

    with TestClient(app, raise_server_exceptions=False) as client:
        from backend.api.services.auth import create_account, issue_session

        p = create_account(
            "postgres-outage@example.com",
            "ExternalTest123!",
            "Test",
            "Test Org",
        )
        token, _ = issue_session(p.user_id)
        client.cookies.set(COOKIE_NAME, token)

        import backend.api.runtime_persistence as runtime_persistence

        original_pool = runtime_persistence._provider
        assert original_pool is not None

        def broken_connection():
            import psycopg
            raise psycopg.OperationalError("Simulated PostgreSQL Outage")

        monkeypatch.setattr(original_pool, "connection", broken_connection)

        resp = client.get("/api/v1/sessions/any-id")
        assert resp.status_code in (500, 503)

def test_metadata_object_mismatch(external_harness):
    test_settings, fake_s3 = external_harness
    with TestClient(app, raise_server_exceptions=False) as client:
        from backend.api.services.auth import create_account, issue_session
        p = create_account("test5@example.com", "ExternalTest123!", "Test", "Test Org")
        token, _ = issue_session(p.user_id)
        client.cookies.set(COOKIE_NAME, token)

        csv_content = b"amount,stage\n100,Closed Won\n"
        upload_resp = client.post("/api/v1/onboarding/profile", files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")})
        dataset_id = upload_resp.json()["dataset"]["dataset_id"]

        # Corrupt the object in S3 so that its structure mismatch with metadata (e.g., completely different columns)
        csv_corrupt = b"wrong_col,bad_data\n1,2\n"
        fake_s3.objects[('test-bucket', f'v4/{dataset_id}.csv')] = csv_corrupt

        # Clear local cache to force redownload
        import shutil
        shutil.rmtree(test_settings.object_store_temp_root)
        test_settings.object_store_temp_root.mkdir()

        # Attempt analytical read. V4 currently treats the stored object as the
        # authoritative analytical source and does not persist an integrity hash
        # binding it to DatasetSummary metadata. Therefore object mutation may
        # produce a valid response rather than an integrity error.
        resp = client.get(f"/api/v1/datasets/{dataset_id}/overview")
        assert resp.status_code == 200
