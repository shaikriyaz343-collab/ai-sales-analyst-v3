from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import ConfigurationError, load_settings
from ..services.auth_postgres import _connect as pg_connect, ensure_schema


REQUIRED_TABLES = (
    "organizations",
    "users",
    "memberships",
    "workspaces",
    "auth_sessions",
    "auth_rate_limits",
    "security_events",
)


def run_cutover_check(database_url: str) -> dict[str, object]:
    settings = load_settings()
    if settings.persistence_mode != "external":
        raise ConfigurationError("Cutover requires V4_PERSISTENCE_MODE=external.")
    if not database_url:
        raise ConfigurationError("V4_DATABASE_URL is required.")

    conn = pg_connect(database_url)
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name = ANY(%s)",
                (list(REQUIRED_TABLES),),
            )
            present = {row[0] for row in cur.fetchall()}

        missing = sorted(set(REQUIRED_TABLES) - present)
        if missing:
            raise ConfigurationError(
                f"PostgreSQL auth schema is incomplete: {', '.join(missing)}"
            )

        return {
            "status": "pass",
            "environment": settings.environment,
            "persistence_mode": settings.persistence_mode,
            "required_tables": list(REQUIRED_TABLES),
            "missing_tables": missing,
            "cutover_allowed": True,
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="V4 C3-D authentication cutover readiness check.")
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    print(json.dumps(run_cutover_check(args.database_url), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
