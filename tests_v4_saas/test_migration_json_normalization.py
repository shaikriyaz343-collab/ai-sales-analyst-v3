import pytest

from backend.api.migrations.auth_sqlite_to_postgres import (
    MigrationError,
    _normalized,
)


def test_metadata_json_string_and_jsonb_structure_are_semantically_equal():
    sqlite_row = {
        "id": "event-1",
        "event_type": "rehearsal_event",
        "created_at": "2026-09-01T16:52:06Z",
        "user_id": "u1",
        "email_hash": "eh",
        "client_ip_hash": "ih",
        "metadata_json": '{"purpose":"c3e","nested":{"b":2,"a":1}}',
    }
    postgres_row = {
        "id": "event-1",
        "event_type": "rehearsal_event",
        "created_at": "2026-09-01T16:52:06+00:00",
        "user_id": "u1",
        "email_hash": "eh",
        "client_ip_hash": "ih",
        "metadata_json": {"nested": {"a": 1, "b": 2}, "purpose": "c3e"},
    }

    assert _normalized(sqlite_row, "security_events") == _normalized(
        postgres_row, "security_events"
    )


def test_invalid_metadata_json_is_a_verification_error():
    row = {
        "id": "event-1",
        "event_type": "rehearsal_event",
        "created_at": "2026-09-01T16:52:06Z",
        "user_id": "u1",
        "email_hash": "eh",
        "client_ip_hash": "ih",
        "metadata_json": "{not-json}",
    }

    with pytest.raises(MigrationError, match="Invalid metadata_json"):
        _normalized(row, "security_events")
