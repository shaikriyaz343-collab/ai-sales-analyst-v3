from datetime import datetime, timezone

import pytest

from backend.api.migrations.auth_sqlite_to_postgres import MigrationError, _normalized


def test_timestamp_string_and_datetime_are_equal():
    source = {'id': 'org-1', 'name': 'Rehearsal Org', 'created_at': '2026-09-01T16:52:06Z'}
    target = {'id': 'org-1', 'name': 'Rehearsal Org', 'created_at': datetime(2026, 9, 1, 16, 52, 6, tzinfo=timezone.utc)}
    assert _normalized(source, 'organizations') == _normalized(target, 'organizations')


def test_metadata_json_text_and_jsonb_are_equal():
    source = {'id': 'event-1', 'event_type': 'rehearsal_event', 'created_at': '2026-09-01T16:52:06Z', 'user_id': 'u1', 'email_hash': 'eh', 'client_ip_hash': 'ih', 'metadata_json': '{"purpose":"c3e","nested":{"b":2,"a":1}}'}
    target = {'id': 'event-1', 'event_type': 'rehearsal_event', 'created_at': datetime(2026, 9, 1, 16, 52, 6, tzinfo=timezone.utc), 'user_id': 'u1', 'email_hash': 'eh', 'client_ip_hash': 'ih', 'metadata_json': {'nested': {'a': 1, 'b': 2}, 'purpose': 'c3e'}}
    assert _normalized(source, 'security_events') == _normalized(target, 'security_events')


def test_invalid_metadata_json_fails_closed():
    row = {'id': 'event-1', 'event_type': 'rehearsal_event', 'created_at': '2026-09-01T16:52:06Z', 'user_id': 'u1', 'email_hash': 'eh', 'client_ip_hash': 'ih', 'metadata_json': '{not-json}'}
    with pytest.raises(MigrationError, match='Invalid metadata_json'):
        _normalized(row, 'security_events')
