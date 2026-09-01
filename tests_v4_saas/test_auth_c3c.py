from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

import backend.api.services.auth as auth
from backend.api.migrations.auth_sqlite_to_postgres import (
    MigrationError,
    MemoryMigrationTarget,
    migrate_sqlite_to_target,
    verify_source_target,
)


@dataclass
class ExternalStoreFake:
    created: int = 0
    authenticated: int = 0
    issued: int = 0
    revoked: int = 0
    revoked_all: int = 0
    listed: int = 0

    def create_account(self, *args):
        self.created += 1
        return auth.Principal(args[4], args[0], args[2], args[5], args[3], "owner", args[6], args[7])

    def authenticate(self, email):
        self.authenticated += 1
        return None

    def issue_session(self, *args):
        self.issued += 1

    def revoke_session(self, *args):
        self.revoked += 1

    def revoke_all_sessions(self, *args):
        self.revoked_all += 1
        return 4

    def principal_from_token(self, *args):
        return None

    def list_workspaces(self, *args):
        self.listed += 1
        return [{"id": "w1", "name": "Main Workspace"}]

    def create_workspace(self, *args):
        return {"id": "w2", "name": args[2]}

    def user_can_access_workspace(self, *args):
        return True

    def consume_rate_limit(self, *args):
        return True

    def record_security_event(self, *args, **kwargs):
        return None

    def list_security_events(self):
        return []


def _create_legacy_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE organizations (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE memberships (user_id TEXT NOT NULL, organization_id TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(user_id, organization_id));
            CREATE TABLE workspaces (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE auth_sessions (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL, created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL);
            CREATE TABLE auth_rate_limits (action TEXT NOT NULL, rate_key TEXT NOT NULL, window_started_at TEXT NOT NULL, attempt_count INTEGER NOT NULL, PRIMARY KEY(action, rate_key));
            CREATE TABLE security_events (id TEXT PRIMARY KEY, event_type TEXT NOT NULL, created_at TEXT NOT NULL, user_id TEXT, email_hash TEXT, client_ip_hash TEXT, metadata_json TEXT NOT NULL);
            """
        )
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        conn.execute("INSERT INTO organizations VALUES(?,?,?)", ("o1", "Org", now))
        conn.execute("INSERT INTO users VALUES(?,?,?,?,?)", ("u1", "owner@example.com", "Owner", "pbkdf2_sha256$1$salt$digest", now))
        conn.execute("INSERT INTO memberships VALUES(?,?,?,?)", ("u1", "o1", "owner", now))
        conn.execute("INSERT INTO workspaces VALUES(?,?,?,?)", ("w1", "o1", "Main", now))
        conn.execute("INSERT INTO auth_sessions VALUES(?,?,?,?,?,?)", ("s1", "u1", "tokenhash", "2099-01-01T00:00:00Z", now, now))
        conn.execute("INSERT INTO auth_rate_limits VALUES(?,?,?,?)", ("login", "ip:x", now, 2))
        conn.execute("INSERT INTO security_events VALUES(?,?,?,?,?,?,?)", ("e1", "login_success", now, "u1", "eh", "ih", "{}"))


def _source_path(tmp_path: Path) -> Path:
    path = tmp_path / "auth.db"
    _create_legacy_db(path)
    return path


def test_migration_supports_pre_c2_sessions(tmp_path):
    target = MemoryMigrationTarget()
    report = migrate_sqlite_to_target(_source_path(tmp_path), target)
    assert report.source_counts["auth_sessions"] == 1
    assert target.tables["auth_sessions"]["s1"]["revoked_at"] is None


def test_migration_preserves_ids_and_password_hash(tmp_path):
    target = MemoryMigrationTarget()
    migrate_sqlite_to_target(_source_path(tmp_path), target)
    assert "u1" in target.tables["users"]
    assert target.tables["users"]["u1"]["password_hash"] == "pbkdf2_sha256$1$salt$digest"
    assert "o1" in target.tables["organizations"]
    assert ("u1", "o1") in target.tables["memberships"]


def test_migration_preserves_session_state(tmp_path):
    target = MemoryMigrationTarget()
    migrate_sqlite_to_target(_source_path(tmp_path), target)
    row = target.tables["auth_sessions"]["s1"]
    assert row["token_hash"] == "tokenhash"
    assert row["expires_at"].endswith("Z")
    assert row["last_seen_at"].endswith("Z")
    assert row["revoked_at"] is None


def test_migration_preserves_rate_limits_and_security_events(tmp_path):
    target = MemoryMigrationTarget()
    migrate_sqlite_to_target(_source_path(tmp_path), target)
    assert target.tables["auth_rate_limits"][("login", "ip:x")]["attempt_count"] == 2
    assert "e1" in target.tables["security_events"]


def test_migration_is_idempotent_for_identical_rows(tmp_path):
    source = _source_path(tmp_path)
    target = MemoryMigrationTarget()
    first = migrate_sqlite_to_target(source, target)
    second = migrate_sqlite_to_target(source, target)
    assert first.source_counts == second.source_counts
    assert second.target_counts == first.target_counts


def test_migration_rejects_conflicting_existing_data(tmp_path):
    source = _source_path(tmp_path)
    target = MemoryMigrationTarget()
    migrate_sqlite_to_target(source, target)
    target.tables["users"]["u1"]["name"] = "Different"
    with pytest.raises(MigrationError, match="verification failed for users"):
        migrate_sqlite_to_target(source, target)


def test_dry_run_does_not_mutate_target(tmp_path):
    target = MemoryMigrationTarget()
    report = migrate_sqlite_to_target(_source_path(tmp_path), target, dry_run=True)
    assert report.target_counts == {}
    assert all(not rows for rows in target.tables.values())
    assert not target.committed


def test_external_auth_delegates_without_using_sqlite(monkeypatch):
    fake = ExternalStoreFake()
    monkeypatch.setattr(auth, "_external_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "_external_auth_store", lambda: fake)
    principal = auth.create_account("external@example.com", "StrongPassword1!", "External", "External Org")
    assert principal.email == "external@example.com"
    assert fake.created == 1


def test_external_auth_session_operations_delegate(monkeypatch):
    fake = ExternalStoreFake()
    monkeypatch.setattr(auth, "_external_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "_external_auth_store", lambda: fake)
    token, expires = auth.issue_session("u1")
    assert token
    assert expires.tzinfo is not None
    auth.revoke_session(token)
    assert auth.revoke_all_sessions("u1") == 4
    assert fake.issued == 1
    assert fake.revoked == 1
    assert fake.revoked_all == 1


def test_external_auth_workspace_operations_delegate(monkeypatch):
    fake = ExternalStoreFake()
    monkeypatch.setattr(auth, "_external_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "_external_auth_store", lambda: fake)
    assert auth.list_workspaces("o1") == [{"id": "w1", "name": "Main Workspace"}]
    assert auth.create_workspace("o1", "Finance")["name"] == "Finance"
    assert auth.user_can_access_workspace("u1", "o1", "w1") is True
    assert fake.listed == 1


def test_external_auth_rate_limit_and_events_delegate(monkeypatch):
    fake = ExternalStoreFake()
    monkeypatch.setattr(auth, "_external_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "_external_auth_store", lambda: fake)
    assert auth.consume_rate_limit("login", "ip:x", 2, 60) is True
    auth.record_security_event("login_success", email="external@example.com")
    assert auth.list_security_events() == []


def test_postgres_schema_has_all_auth_tables():
    from backend.api.services.auth_postgres import AUTH_TABLE_SQL
    for table in ("organizations", "users", "memberships", "workspaces", "auth_sessions", "auth_rate_limits", "security_events"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in AUTH_TABLE_SQL


def test_verify_source_target_detects_extra_rows(tmp_path):
    source = _source_path(tmp_path)
    target = MemoryMigrationTarget()
    source_rows_report = migrate_sqlite_to_target(source, target)
    target.tables["users"]["extra"] = {
        "id": "extra", "email": "x@example.com", "name": "x", "password_hash": "p", "created_at": "2099-01-01T00:00:00Z"
    }
    with sqlite3.connect(source) as conn:
        rows = {"users": [dict(zip([d[0] for d in conn.execute("SELECT * FROM users").description], r)) for r in conn.execute("SELECT * FROM users")]} 
    # Build complete source through the canonical reader by running a fresh migration target.
    clean = MemoryMigrationTarget()
    migrate_sqlite_to_target(source, clean)
    with pytest.raises(MigrationError, match="extra"):
        verify_source_target(
            {table: list(clean.tables[table].values()) for table in clean.tables},
            target,
        )
