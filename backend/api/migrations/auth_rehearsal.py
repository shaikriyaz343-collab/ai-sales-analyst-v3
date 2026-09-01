from __future__ import annotations

import argparse
import gc
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .auth_sqlite_to_postgres import (
    MigrationError,
    PostgresMigrationTarget,
    _read_source,
    migrate_sqlite_to_target,
    verify_source_target,
)
from ..services.auth import init_db
from ..services.auth_postgres import PostgresAuthStore


@dataclass(frozen=True)
class RehearsalResult:
    source_counts: dict[str, int]
    target_counts: dict[str, int]
    verified_tables: tuple[str, ...]
    rollback_snapshot_created: bool


def _seed_sqlite(source: Path) -> dict[str, str]:
    """Create a disposable auth DB using the real auth schema and API.

    Returns the expected identity/session material without exposing plaintext
    passwords or session tokens outside this process.
    """
    import backend.api.services.auth as auth

    old_storage = auth.AUTH_STORAGE
    old_db = auth.AUTH_DB
    try:
        auth.AUTH_STORAGE = source.parent
        auth.AUTH_DB = source
        init_db()

        owner = auth.create_account(
            "rehearsal-owner@example.com",
            "StrongPassword1!",
            "Rehearsal Owner",
            "Rehearsal Org",
        )
        token, _ = auth.issue_session(owner.user_id)
        auth.record_security_event(
            "rehearsal_event",
            email=owner.email,
            client_ip="198.51.100.10",
            user_id=owner.user_id,
            metadata={"purpose": "c3e"},
        )
        auth.consume_rate_limit("login", "rehearsal-key", 8, 900)

        # Create a second organization to prove isolation data exists.
        auth.create_account(
            "rehearsal-second@example.com",
            "StrongPassword2!",
            "Second Owner",
            "Second Org",
        )

        return {
            "owner_user_id": owner.user_id,
            "session_token_hash": auth._token_hash(token),
        }
    finally:
        auth.AUTH_STORAGE = old_storage
        auth.AUTH_DB = old_db
        # The auth service uses `with sqlite3.Connection(...)` blocks. SQLite
        # commits/rolls back on context exit but does not close the connection.
        # Force released local connections to be finalized before Windows temp
        # directory cleanup attempts to unlink the database file.
        gc.collect()


def create_rehearsal_source(root: Path) -> tuple[Path, dict[str, str]]:
    root.mkdir(parents=True, exist_ok=True)
    source = root / "auth-rehearsal.db"
    material = _seed_sqlite(source)
    return source, material


def snapshot_source(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def run_memory_rehearsal() -> RehearsalResult:
    from .auth_sqlite_to_postgres import MemoryMigrationTarget

    with tempfile.TemporaryDirectory(prefix="v4-c3e-") as tmp:
        root = Path(tmp)
        source, _ = create_rehearsal_source(root)
        snapshot = snapshot_source(source, root / "rollback" / "auth.db")

        source_rows = _read_source(source)
        target = MemoryMigrationTarget()
        report = migrate_sqlite_to_target(source, target, verify=True)
        snapshot_created = snapshot.exists()
        return RehearsalResult(
            source_counts=report.source_counts,
            target_counts=report.target_counts,
            verified_tables=report.verified_tables,
            rollback_snapshot_created=snapshot_created,
        )


def run_postgres_rehearsal(database_url: str) -> RehearsalResult:
    """Run against an explicitly supplied disposable PostgreSQL database.

    Safety:
    - V4_ENVIRONMENT=production is rejected.
    - V4_REHEARSAL_DATABASE_URL must be set to the exact supplied URL.
    """
    if os.getenv("V4_ENVIRONMENT", "development").lower() == "production":
        raise MigrationError("C3-E rehearsal is forbidden when V4_ENVIRONMENT=production.")
    if os.getenv("V4_REHEARSAL_DATABASE_URL") != database_url:
        raise MigrationError(
            "C3-E PostgreSQL rehearsal requires V4_REHEARSAL_DATABASE_URL to match --database-url."
        )

    from .auth_sqlite_to_postgres import migrate_sqlite_to_postgres

    with tempfile.TemporaryDirectory(prefix="v4-c3e-") as tmp:
        root = Path(tmp)
        source, _ = create_rehearsal_source(root)
        snapshot = snapshot_source(source, root / "rollback" / "auth.db")

        report = migrate_sqlite_to_postgres(source, database_url, dry_run=False, verify=True)
        target = PostgresMigrationTarget(database_url)
        try:
            target_rows = verify_source_target(_read_source(source), target)
        finally:
            target.close()

        snapshot_created = snapshot.exists()
        return RehearsalResult(
            source_counts=report.source_counts,
            target_counts=target_rows,
            verified_tables=report.verified_tables,
            rollback_snapshot_created=snapshot_created,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="V4 C3-E production migration rehearsal.")
    parser.add_argument(
        "--mode",
        choices=("memory", "postgres"),
        default="memory",
        help="memory is deterministic/offline; postgres requires an explicit disposable PostgreSQL URL.",
    )
    parser.add_argument("--database-url", default="", help="Disposable PostgreSQL URL for --mode postgres.")
    args = parser.parse_args()

    try:
        if args.mode == "memory":
            result = run_memory_rehearsal()
        else:
            if not args.database_url:
                raise MigrationError("--database-url is required for --mode postgres.")
            result = run_postgres_rehearsal(args.database_url)

        print("C3-E rehearsal: PASS")
        for table in result.verified_tables:
            print(f"  {table}: {result.source_counts[table]} -> {result.target_counts[table]}")
        print(f"  rollback snapshot created: {result.rollback_snapshot_created}")
        return 0
    except Exception as exc:
        print(f"C3-E rehearsal: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
