from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from backend.api.migrations import auth_sqlite_to_postgres as migration
from backend.api.migrations.auth_sqlite_to_postgres import (
    MigrationError,
    MemoryMigrationTarget,
    migrate_sqlite_to_target,
)
from backend.api.migrations.auth_preflight import run_preflight


def _legacy_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE organizations (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
                            password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE memberships (user_id TEXT NOT NULL, organization_id TEXT NOT NULL, role TEXT NOT NULL,
                                  created_at TEXT NOT NULL, PRIMARY KEY(user_id, organization_id));
        CREATE TABLE workspaces (id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL,
                                 created_at TEXT NOT NULL, UNIQUE(organization_id,name));
        CREATE TABLE auth_sessions (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
                                    expires_at TEXT NOT NULL, created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL);
        CREATE TABLE auth_rate_limits (action TEXT NOT NULL, rate_key TEXT NOT NULL,
                                       window_started_at TEXT NOT NULL, attempt_count INTEGER NOT NULL,
                                       PRIMARY KEY(action, rate_key));
        CREATE TABLE security_events (id TEXT PRIMARY KEY, event_type TEXT NOT NULL, created_at TEXT NOT NULL,
                                       user_id TEXT, email_hash TEXT, client_ip_hash TEXT, metadata_json TEXT NOT NULL);
        INSERT INTO organizations VALUES ('org1','Acme','2026-01-01T00:00:00Z');
        INSERT INTO users VALUES ('u1','owner@example.com','Owner','pbkdf2_sha256$310000$aa$bb','2026-01-01T00:00:00Z');
        INSERT INTO memberships VALUES ('u1','org1','owner','2026-01-01T00:00:00Z');
        INSERT INTO workspaces VALUES ('w1','org1','Main','2026-01-01T00:00:00Z');
        INSERT INTO auth_sessions VALUES ('s1','u1','hash','2026-01-08T00:00:00Z','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z');
        INSERT INTO auth_rate_limits VALUES ('login','ip:hash','2026-01-01T00:00:00Z',1);
        INSERT INTO security_events VALUES ('e1','login_success','2026-01-01T00:00:00Z','u1','eh','ih','{}');
        """
    )
    conn.commit()
    conn.close()


def test_migration_is_read_only_by_default(tmp_path: Path):
    db = tmp_path / "auth.db"
    _legacy_db(db)
    target = MemoryMigrationTarget()
    report = migrate_sqlite_to_target(db, target, dry_run=True)
    assert report.source_counts["users"] == 1
    assert target.committed is False
    assert target.tables["users"] == {}


def test_migration_import_preserves_ids_and_verifies(tmp_path: Path):
    db = tmp_path / "auth.db"
    _legacy_db(db)
    target = MemoryMigrationTarget()
    report = migrate_sqlite_to_target(db, target, dry_run=False, verify=True)
    assert report.target_counts["organizations"] == 1
    assert report.verified_tables == migration.TABLE_ORDER
    assert target.committed is True
    assert "u1" in target.tables["users"]


def test_migration_rolls_back_on_target_failure(tmp_path: Path):
    class FailingTarget(MemoryMigrationTarget):
        def insert_rows(self, table, columns, rows):
            if table == "workspaces":
                raise RuntimeError("boom")
            super().insert_rows(table, columns, rows)

    db = tmp_path / "auth.db"
    _legacy_db(db)
    with pytest.raises(MigrationError, match="Authentication migration failed"):
        migrate_sqlite_to_target(db, FailingTarget(), dry_run=False, verify=True)


def test_legacy_sessions_are_migrated_with_null_revocation(tmp_path: Path):
    db = tmp_path / "auth.db"
    _legacy_db(db)
    rows = migration._read_source(db)["auth_sessions"]
    assert rows[0]["revoked_at"] is None


def test_cli_requires_apply_for_writes():
    import inspect
    source = inspect.getsource(migration.main)
    assert '"--apply"' in source
    assert "dry_run = not args.apply" in source
