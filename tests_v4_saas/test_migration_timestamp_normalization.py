from datetime import datetime, timezone

from backend.api.migrations.auth_sqlite_to_postgres import _normalized


def test_timestamp_normalization_treats_sqlite_and_postgres_values_as_equal():
    sqlite_row = {
        "id": "org-1",
        "name": "Rehearsal Org",
        "created_at": "2026-09-01T16:52:06Z",
    }
    postgres_row = {
        "id": "org-1",
        "name": "Rehearsal Org",
        "created_at": datetime(2026, 9, 1, 16, 52, 6, tzinfo=timezone.utc),
    }

    assert _normalized(sqlite_row, "organizations") == _normalized(
        postgres_row, "organizations"
    )
