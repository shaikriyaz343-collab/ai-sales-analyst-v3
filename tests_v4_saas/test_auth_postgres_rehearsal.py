from __future__ import annotations

import os

import pytest

from backend.api.migrations.auth_postgres_rehearsal import run_real_postgres_rehearsal


pytestmark = pytest.mark.skipif(
    not os.getenv("V4_REHEARSAL_DATABASE_URL"),
    reason="Set V4_REHEARSAL_DATABASE_URL to run the disposable PostgreSQL rehearsal.",
)


def test_real_postgres_rehearsal():
    result = run_real_postgres_rehearsal(os.environ["V4_REHEARSAL_DATABASE_URL"])

    assert result["password_hash_verified"] is True
    assert result["active_session_verified"] is True
    assert result["tenant_isolation_verified"] is True
    assert result["revocation_verified"] is True
    assert result["security_events_verified"] is True
    assert result["rate_limits_verified"] is True
    assert result["source_counts"] == result["target_counts"]
