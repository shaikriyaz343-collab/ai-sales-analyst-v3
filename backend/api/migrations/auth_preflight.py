from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from ..config import ConfigurationError, load_settings
from ..services.auth_postgres import AuthPersistenceError, ensure_schema, _connect as pg_connect
from .auth_sqlite_to_postgres import REQUIRED_COLUMNS, TABLE_ORDER, MigrationError, _read_source


SCHEMA_VERSION = 1


def _sqlite_integrity(source: Path) -> dict[str, Any]:
    if not source.exists():
        raise MigrationError(f"SQLite source database does not exist: {source}")
    conn = sqlite3.connect(source)
    try:
        fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_violations:
            raise MigrationError(f"SQLite foreign-key integrity check failed: {fk_violations[:3]}")
        rows = conn.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('table','index')"
        ).fetchall()
        return {"objects": len(rows), "foreign_key_violations": len(fk_violations)}
    finally:
        conn.close()


def check_postgres(database_url: str) -> dict[str, Any]:
    if not database_url:
        raise ConfigurationError("V4_DATABASE_URL is required.")
    conn = pg_connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT to_regclass('public.users'), to_regclass('public.organizations'), "
                "to_regclass('public.auth_sessions')"
            )
            tables = cur.fetchone()
        return {"postgres_version": version, "auth_tables_present": all(tables)}
    finally:
        conn.close()


def run_preflight(source: Path, database_url: str, *, require_production: bool = False) -> dict[str, Any]:
    settings = load_settings()
    if require_production and settings.environment != "production":
        raise ConfigurationError("Production preflight requires V4_ENVIRONMENT=production.")
    if settings.persistence_mode != "external":
        raise ConfigurationError("C3-D preflight requires V4_PERSISTENCE_MODE=external.")
    source_summary = _sqlite_integrity(source)
    source_rows = _read_source(source)
    counts = {table: len(rows) for table, rows in source_rows.items()}
    target_summary = check_postgres(database_url)
    return {
        "status": "pass",
        "environment": settings.environment,
        "persistence_mode": settings.persistence_mode,
        "source": str(source),
        "source_counts": counts,
        "source_integrity": source_summary,
        "target": target_summary,
        "schema_version_required": SCHEMA_VERSION,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="V4 C3-D production authentication preflight.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--require-production", action="store_true")
    args = parser.parse_args()

    print(json.dumps(run_preflight(
        args.source,
        args.database_url,
        require_production=args.require_production,
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
