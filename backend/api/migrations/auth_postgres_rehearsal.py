from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from .auth_sqlite_to_postgres import (
    MigrationError,
    PostgresMigrationTarget,
    _read_source,
    migrate_sqlite_to_postgres,
    verify_source_target,
)
from .auth_rehearsal import create_rehearsal_source
from ..services.auth import _verify_password
from ..services.auth_postgres import PostgresAuthStore


def _assert_not_production() -> None:
    if os.getenv("V4_ENVIRONMENT", "development").lower() == "production":
        raise MigrationError("C3-F PostgreSQL rehearsal is forbidden when V4_ENVIRONMENT=production.")


def _reset_rehearsal_target(database_url: str) -> None:
    from urllib.parse import urlparse

    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    database_name = (parsed.path or "").lstrip("/")

    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise MigrationError(
            "C3-F reset is restricted to a local PostgreSQL rehearsal database."
        )
    if database_name != "v4_auth_rehearsal":
        raise MigrationError(
            "C3-F reset is restricted to the database named v4_auth_rehearsal."
        )

    from ..services.auth_postgres import _connect, ensure_schema

    with _connect(database_url) as conn:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE "
                "security_events, auth_rate_limits, auth_sessions, "
                "workspaces, memberships, users, organizations "
                "RESTART IDENTITY CASCADE"
            )
        conn.commit()


def run_real_postgres_rehearsal(database_url: str) -> dict[str, object]:
    _assert_not_production()

    expected_url = os.getenv("V4_REHEARSAL_DATABASE_URL")
    if expected_url != database_url:
        raise MigrationError(
            "Set V4_REHEARSAL_DATABASE_URL to the exact disposable PostgreSQL URL before running C3-F."
        )

    with tempfile.TemporaryDirectory(prefix="v4-c3f-") as tmp:
        root = Path(tmp)
        source, material = create_rehearsal_source(root)
        _reset_rehearsal_target(database_url)

        # Prove the dry-run performs no target writes.
        dry = migrate_sqlite_to_postgres(
            source,
            database_url,
            dry_run=True,
            verify=True,
        )
        if dry.target_counts:
            raise MigrationError("C3-F dry-run unexpectedly reported target writes.")

        # Run the actual migration only against the explicitly supplied
        # disposable rehearsal database.
        report = migrate_sqlite_to_postgres(
            source,
            database_url,
            dry_run=False,
            verify=True,
        )

        target = PostgresMigrationTarget(database_url)
        try:
            target_counts = verify_source_target(_read_source(source), target)
        finally:
            target.close()

        store = PostgresAuthStore(database_url)

        # Password hash portability: the password itself is never exported.
        auth_row = store.authenticate("rehearsal-owner@example.com")
        if not auth_row:
            raise MigrationError("Migrated rehearsal user cannot be loaded from PostgreSQL.")
        if not _verify_password(
            "StrongPassword1!",
            auth_row["password_hash"],
        ):
            raise MigrationError("Migrated password hash does not authenticate.")

        # Existing session hash remains valid after migration.
        import backend.api.services.auth as auth

        token_hash = material["session_token_hash"]
        principal = store.principal_from_token(
            token_hash,
            auth._utc_now(),
            auth.SESSION_IDLE_SECONDS,
        )
        if principal is None:
            raise MigrationError("Migrated active session could not be authenticated.")

        # Tenant/workspace boundary survives the migration.
        own_workspaces = store.list_workspaces(principal.organization_id)
        if len(own_workspaces) != 1:
            raise MigrationError("Expected exactly one rehearsal workspace.")
        own_workspace_id = own_workspaces[0]["id"]
        if not store.user_can_access_workspace(
            principal.user_id,
            principal.organization_id,
            own_workspace_id,
        ):
            raise MigrationError("Rehearsal owner lost access to its own workspace.")

        other_org_id = _lookup_other_org_id(store, principal.organization_id)
        other_workspace_id = store.list_workspaces(other_org_id)[0]["id"]
        if store.user_can_access_workspace(
            principal.user_id,
            principal.organization_id,
            other_workspace_id,
        ):
            raise MigrationError("Cross-tenant workspace access became possible.")

        # Revocation remains effective after migration.
        store.revoke_session(token_hash, auth._iso(auth._utc_now()))
        if store.principal_from_token(
            token_hash,
            auth._utc_now(),
            auth.SESSION_IDLE_SECONDS,
        ) is not None:
            raise MigrationError("Migrated session remained usable after revocation.")

        events = store.list_security_events()
        if not any(event["event_type"] == "rehearsal_event" for event in events):
            raise MigrationError("Migrated security event history is incomplete.")

        allowed = store.consume_rate_limit("login", "rehearsal-key-2", 1, 900)
        limited = store.consume_rate_limit("login", "rehearsal-key-2", 1, 900)
        if not allowed or limited:
            raise MigrationError("Migrated PostgreSQL rate-limit behavior is incorrect.")

        return {
            "source_counts": report.source_counts,
            "target_counts": target_counts,
            "verified_tables": report.verified_tables,
            "password_hash_verified": True,
            "active_session_verified": True,
            "tenant_isolation_verified": True,
            "revocation_verified": True,
            "security_events_verified": True,
            "rate_limits_verified": True,
        }


def _lookup_other_org_id(store: PostgresAuthStore, own_org_id: str) -> str:
    from ..services.auth_postgres import _connect
    with _connect(store.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM organizations WHERE id <> %s ORDER BY created_at ASC LIMIT 1",
                (own_org_id,),
            )
            row = cur.fetchone()
    if not row:
        raise MigrationError("Rehearsal target is missing the second organization.")
    return row[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the V4 C3-F real PostgreSQL migration rehearsal."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("V4_REHEARSAL_DATABASE_URL", ""),
        help="Disposable PostgreSQL database URL.",
    )
    args = parser.parse_args()

    if not args.database_url:
        print("C3-F rehearsal requires --database-url or V4_REHEARSAL_DATABASE_URL.")
        return 2

    try:
        result = run_real_postgres_rehearsal(args.database_url)
    except Exception as exc:
        print(f"C3-F PostgreSQL rehearsal: FAIL: {exc}")
        return 1

    print("C3-F PostgreSQL rehearsal: PASS")
    for table in result["verified_tables"]:
        print(
            f"  {table}: "
            f"{result['source_counts'][table]} -> {result['target_counts'][table]}"
        )
    print("  password hash: verified")
    print("  active session: verified")
    print("  tenant isolation: verified")
    print("  revocation: verified")
    print("  security events: verified")
    print("  rate limits: verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
