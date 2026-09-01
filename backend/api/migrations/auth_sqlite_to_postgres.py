from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from ..services.auth_postgres import AUTH_TABLE_SQL, AuthPersistenceError, _connect as pg_connect, ensure_schema

TABLE_ORDER = (
    "organizations",
    "users",
    "memberships",
    "workspaces",
    "auth_sessions",
    "auth_rate_limits",
    "security_events",
)

REQUIRED_COLUMNS = {
    "organizations": {"id", "name", "created_at"},
    "users": {"id", "email", "name", "password_hash", "created_at"},
    "memberships": {"user_id", "organization_id", "role", "created_at"},
    "workspaces": {"id", "organization_id", "name", "created_at"},
    "auth_sessions": {"id", "user_id", "token_hash", "expires_at", "created_at", "last_seen_at", "revoked_at"},
    "auth_rate_limits": {"action", "rate_key", "window_started_at", "attempt_count"},
    "security_events": {"id", "event_type", "created_at", "user_id", "email_hash", "client_ip_hash", "metadata_json"},
}


class MigrationError(RuntimeError):
    """Raised when an authentication migration cannot be completed safely."""


@dataclass(frozen=True)
class MigrationReport:
    source_counts: dict[str, int]
    target_counts: dict[str, int]
    verified_tables: tuple[str, ...]


class MigrationTarget(Protocol):
    def ensure_schema(self) -> None: ...
    def insert_rows(self, table: str, columns: list[str], rows: list[dict[str, Any]]) -> None: ...
    def fetch_rows(self, table: str, columns: list[str]) -> list[dict[str, Any]]: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class PostgresMigrationTarget:
    def __init__(self, database_url: str) -> None:
        self.connection = pg_connect(database_url)

    def ensure_schema(self) -> None:
        ensure_schema(self.connection)

    def insert_rows(self, table: str, columns: list[str], rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        placeholders = ",".join(["%s"] * len(columns))
        column_sql = ",".join(columns)
        sql = f"INSERT INTO {table}({column_sql}) VALUES({placeholders}) ON CONFLICT DO NOTHING"
        with self.connection.cursor() as cur:
            cur.executemany(sql, [[_postgres_value(table, c, row[c]) for c in columns] for row in rows])

    def fetch_rows(self, table: str, columns: list[str]) -> list[dict[str, Any]]:
        with self.connection.cursor() as cur:
            cur.execute(f"SELECT {','.join(columns)} FROM {table} ORDER BY 1")
            return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()


class MemoryMigrationTarget:
    """Deterministic target used by migration tests without requiring PostgreSQL."""

    def __init__(self) -> None:
        self.tables: dict[str, dict[Any, dict[str, Any]]] = {table: {} for table in TABLE_ORDER}
        self.committed = False
        self.rolled_back = False
        self.schema_ready = False

    def ensure_schema(self) -> None:
        self.schema_ready = True

    def insert_rows(self, table: str, columns: list[str], rows: list[dict[str, Any]]) -> None:
        if not self.schema_ready:
            raise MigrationError("Target schema has not been initialized.")
        key_column = "id" if "id" in columns else ("user_id", "organization_id") if table == "memberships" else ("action", "rate_key")
        for row in rows:
            key = tuple(row[k] for k in key_column) if isinstance(key_column, tuple) else row[key_column]
            self.tables[table].setdefault(key, dict(row))

    def fetch_rows(self, table: str, columns: list[str]) -> list[dict[str, Any]]:
        return [dict(row) for row in self.tables[table].values()]

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True



def _postgres_value(table: str, column: str, value: Any) -> Any:
    if table == "security_events" and column == "metadata_json":
        try:
            from psycopg.types.json import Json
        except ImportError as exc:
            raise MigrationError("psycopg is required for PostgreSQL authentication migration.") from exc
        return Json(json.loads(value or "{}") if isinstance(value, str) else (value or {}))
    if column.endswith("_at") or column == "created_at":
        return _as_datetime(value)
    return value


def _as_datetime(value: Any) -> Any:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _sqlite_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def _sqlite_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def _read_source(source: Path) -> dict[str, list[dict[str, Any]]]:
    if not source.exists():
        raise MigrationError(f"SQLite source database does not exist: {source}")
    connection = sqlite3.connect(source)
    connection.row_factory = sqlite3.Row
    try:
        tables = _sqlite_tables(connection)
        missing = [table for table in TABLE_ORDER if table not in tables]
        if missing:
            raise MigrationError(f"SQLite auth database is missing tables: {', '.join(missing)}")
        result: dict[str, list[dict[str, Any]]] = {}
        for table in TABLE_ORDER:
            columns = _sqlite_columns(connection, table)
            required = REQUIRED_COLUMNS[table]
            if table == "auth_sessions" and "revoked_at" not in columns:
                result[table] = [
                    dict(row) | {"revoked_at": None}
                    for row in connection.execute("SELECT id,user_id,token_hash,expires_at,created_at,last_seen_at FROM auth_sessions ORDER BY id")
                ]
                continue
            missing_columns = required - columns
            if missing_columns:
                raise MigrationError(f"SQLite table {table} is missing columns: {', '.join(sorted(missing_columns))}")
            result[table] = [dict(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]
        return result
    finally:
        connection.close()


def _critical_columns(table: str) -> list[str]:
    return {
        "organizations": ["id", "name", "created_at"],
        "users": ["id", "email", "name", "password_hash", "created_at"],
        "memberships": ["user_id", "organization_id", "role", "created_at"],
        "workspaces": ["id", "organization_id", "name", "created_at"],
        "auth_sessions": ["id", "user_id", "token_hash", "expires_at", "created_at", "last_seen_at", "revoked_at"],
        "auth_rate_limits": ["action", "rate_key", "window_started_at", "attempt_count"],
        "security_events": ["id", "event_type", "created_at", "user_id", "email_hash", "client_ip_hash", "metadata_json"],
    }[table]


def _normalized(row: dict[str, Any], table: str) -> tuple[Any, ...]:
    values: list[Any] = []
    for column in _critical_columns(table):
        value = row.get(column)
        if isinstance(value, datetime):
            value = value.isoformat().replace("+00:00", "Z")
        elif column == "metadata_json" and isinstance(value, (dict, list)):
            value = json.dumps(value, sort_keys=True, separators=(",", ":"))
        values.append(value)
    return tuple(values)


def verify_source_target(source_rows: dict[str, list[dict[str, Any]]], target: MigrationTarget) -> dict[str, int]:
    target_counts: dict[str, int] = {}
    for table in TABLE_ORDER:
        columns = _critical_columns(table)
        target_rows = target.fetch_rows(table, columns)
        target_counts[table] = len(target_rows)
        source_by_key = {_row_key(table, row): _normalized(row, table) for row in source_rows[table]}
        target_by_key = {_row_key(table, row): _normalized(row, table) for row in target_rows}
        if source_by_key != target_by_key:
            missing = sorted(set(source_by_key) - set(target_by_key), key=str)
            extra = sorted(set(target_by_key) - set(source_by_key), key=str)
            mismatched = sorted(
                key for key in set(source_by_key) & set(target_by_key)
                if source_by_key[key] != target_by_key[key]
            )
            raise MigrationError(
                f"Migration verification failed for {table}: "
                f"missing={missing[:3]}, extra={extra[:3]}, mismatched={mismatched[:3]}"
            )
    return target_counts


def _row_key(table: str, row: dict[str, Any]) -> Any:
    if table == "memberships":
        return row["user_id"], row["organization_id"]
    if table == "auth_rate_limits":
        return row["action"], row["rate_key"]
    return row["id"]


def migrate_sqlite_to_target(source: Path, target: MigrationTarget, *, dry_run: bool = False, verify: bool = True) -> MigrationReport:
    source_rows = _read_source(source)
    source_counts = {table: len(rows) for table, rows in source_rows.items()}
    if dry_run:
        return MigrationReport(source_counts, {}, ())

    try:
        target.ensure_schema()
        for table in TABLE_ORDER:
            rows = source_rows[table]
            if not rows:
                continue
            columns = _critical_columns(table)
            target.insert_rows(table, columns, rows)
        target_counts = verify_source_target(source_rows, target) if verify else {
            table: len(target.fetch_rows(table, _critical_columns(table))) for table in TABLE_ORDER
        }
        target.commit()
    except Exception as exc:
        target.rollback()
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError(f"Authentication migration failed: {exc}") from exc

    return MigrationReport(source_counts, target_counts, TABLE_ORDER if verify else ())


def migrate_sqlite_to_postgres(source: Path, database_url: str, *, dry_run: bool = False, verify: bool = True) -> MigrationReport:
    target = PostgresMigrationTarget(database_url)
    try:
        return migrate_sqlite_to_target(source, target, dry_run=dry_run, verify=verify)
    finally:
        target.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate V4 authentication SQLite state into PostgreSQL.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args()

    report = migrate_sqlite_to_postgres(
        args.source,
        args.database_url,
        dry_run=args.dry_run,
        verify=not args.no_verify,
    )
    print(json.dumps({"source_counts": report.source_counts, "target_counts": report.target_counts, "verified_tables": report.verified_tables}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
