from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config import settings


class AuthPersistenceError(RuntimeError):
    """Raised when PostgreSQL authentication persistence is unavailable."""


AUTH_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS memberships (
    user_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, organization_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    UNIQUE (organization_id, name)
);
CREATE TABLE IF NOT EXISTS auth_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS auth_rate_limits (
    action TEXT NOT NULL,
    rate_key TEXT NOT NULL,
    window_started_at TIMESTAMPTZ NOT NULL,
    attempt_count INTEGER NOT NULL,
    PRIMARY KEY (action, rate_key)
);
CREATE TABLE IF NOT EXISTS security_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    user_id TEXT,
    email_hash TEXT,
    client_ip_hash TEXT,
    metadata_json JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pg_memberships_org ON memberships(organization_id);
CREATE INDEX IF NOT EXISTS idx_pg_workspaces_org ON workspaces(organization_id);
CREATE INDEX IF NOT EXISTS idx_pg_sessions_token ON auth_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_pg_security_events_created ON security_events(created_at);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _connect(database_url: str):
    try:
        import psycopg
    except ImportError as exc:
        raise AuthPersistenceError(
            "psycopg is required for external authentication persistence."
        ) from exc
    return psycopg.connect(database_url)


def ensure_schema(connection: Any) -> None:
    with connection.cursor() as cur:
        for statement in AUTH_TABLE_SQL.split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)
    connection.commit()


def _json(value: dict[str, str] | None) -> Any:
    try:
        from psycopg.types.json import Json
    except ImportError as exc:
        raise AuthPersistenceError("psycopg is required for JSONB metadata.") from exc
    return Json(value or {})


def _principal(row: Any):
    from .auth import Principal

    return Principal(
        row["user_id"],
        row["email"],
        row["name"],
        row["organization_id"],
        row["organization_name"],
        row["role"],
        row["workspace_id"],
        row["workspace_name"],
    )


class PostgresAuthStore:
    """Production authentication store backed by PostgreSQL."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or settings.database_url
        if not self.database_url:
            raise AuthPersistenceError(
                "V4_DATABASE_URL is required for external authentication persistence."
            )
        self._initialize()

    def _initialize(self) -> None:
        with _connect(self.database_url) as conn:
            ensure_schema(conn)

    def create_account(
        self, email: str, password_hash: str, name: str, organization_name: str,
        user_id: str, organization_id: str, workspace_id: str, workspace_name: str, now: str,
    ):
        try:
            with _connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                    if cur.fetchone():
                        raise ValueError("An account with that email already exists.")
                    cur.execute(
                        "INSERT INTO users(id,email,name,password_hash,created_at) VALUES(%s,%s,%s,%s,%s)",
                        (user_id, email, name, password_hash, now),
                    )
                    cur.execute(
                        "INSERT INTO organizations(id,name,created_at) VALUES(%s,%s,%s)",
                        (organization_id, organization_name, now),
                    )
                    cur.execute(
                        "INSERT INTO memberships(user_id,organization_id,role,created_at) VALUES(%s,%s,%s,%s)",
                        (user_id, organization_id, "owner", now),
                    )
                    cur.execute(
                        "INSERT INTO workspaces(id,organization_id,name,created_at) VALUES(%s,%s,%s,%s)",
                        (workspace_id, organization_id, workspace_name, now),
                    )
                conn.commit()
        except ValueError:
            raise
        except Exception as exc:
            if "duplicate key" in str(exc).lower():
                raise ValueError("An account with that email already exists.") from exc
            raise
        from .auth import Principal
        return Principal(user_id, email, name, organization_id, organization_name, "owner", workspace_id, workspace_name)

    def authenticate(self, email: str):
        with _connect(self.database_url) as conn:
            with conn.cursor(row_factory=_dict_row_factory()) as cur:
                cur.execute(
                    """
                    SELECT u.id AS user_id, u.email, u.name, u.password_hash,
                           o.id AS organization_id, o.name AS organization_name,
                           m.role, w.id AS workspace_id, w.name AS workspace_name
                    FROM users u
                    JOIN memberships m ON m.user_id = u.id
                    JOIN organizations o ON o.id = m.organization_id
                    JOIN workspaces w ON w.organization_id = o.id
                    WHERE u.email = %s
                    ORDER BY w.created_at ASC
                    LIMIT 1
                    """,
                    (email,),
                )
                return cur.fetchone()

    def issue_session(self, user_id: str, token_hash: str, expires_at: str, created_at: str, session_id: str) -> None:
        with _connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_sessions(id,user_id,token_hash,expires_at,created_at,last_seen_at,revoked_at)
                    VALUES(%s,%s,%s,%s,%s,%s,NULL)
                    """,
                    (session_id, user_id, token_hash, expires_at, created_at, created_at),
                )
            conn.commit()

    def revoke_session(self, token_hash: str, now: str) -> None:
        with _connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_sessions SET revoked_at = %s WHERE token_hash = %s AND revoked_at IS NULL",
                    (now, token_hash),
                )
            conn.commit()

    def revoke_all_sessions(self, user_id: str, now: str) -> int:
        with _connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_sessions SET revoked_at = %s WHERE user_id = %s AND revoked_at IS NULL",
                    (now, user_id),
                )
                count = cur.rowcount
            conn.commit()
            return count

    def principal_from_token(self, token_hash: str, now: datetime, idle_seconds: int):
        with _connect(self.database_url) as conn:
            with conn.cursor(row_factory=_dict_row_factory()) as cur:
                cur.execute(
                    """
                    SELECT u.id AS user_id, u.email, u.name,
                           o.id AS organization_id, o.name AS organization_name,
                           m.role, w.id AS workspace_id, w.name AS workspace_name,
                           s.expires_at, s.created_at, s.last_seen_at,
                           s.revoked_at, s.id AS session_id
                    FROM auth_sessions s
                    JOIN users u ON u.id = s.user_id
                    JOIN memberships m ON m.user_id = u.id
                    JOIN organizations o ON o.id = m.organization_id
                    JOIN workspaces w ON w.organization_id = o.id
                    WHERE s.token_hash = %s
                    ORDER BY w.created_at ASC
                    LIMIT 1
                    """,
                    (token_hash,),
                )
                row = cur.fetchone()
                if not row or row["revoked_at"] is not None:
                    return None
                expires = _as_utc(row["expires_at"])
                last_seen = _as_utc(row["last_seen_at"])
                if expires <= now:
                    return None
                if last_seen + timedelta(seconds=idle_seconds) <= now:
                    cur.execute(
                        "UPDATE auth_sessions SET revoked_at = %s WHERE id = %s AND revoked_at IS NULL",
                        (now, row["session_id"]),
                    )
                    conn.commit()
                    return None
                cur.execute(
                    "UPDATE auth_sessions SET last_seen_at = %s WHERE id = %s",
                    (now, row["session_id"]),
                )
                conn.commit()
                return _principal(row)

    def list_workspaces(self, organization_id: str) -> list[dict[str, str]]:
        with _connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id,name FROM workspaces WHERE organization_id = %s ORDER BY created_at ASC",
                    (organization_id,),
                )
                return [{"id": row[0], "name": row[1]} for row in cur.fetchall()]

    def create_workspace(self, organization_id: str, workspace_id: str, name: str, now: str) -> dict[str, str]:
        try:
            with _connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO workspaces(id,organization_id,name,created_at) VALUES(%s,%s,%s,%s)",
                        (workspace_id, organization_id, name, now),
                    )
                conn.commit()
        except Exception as exc:
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                raise ValueError("A workspace with that name already exists.") from exc
            raise
        return {"id": workspace_id, "name": name}

    def user_can_access_workspace(self, user_id: str, organization_id: str, workspace_id: str) -> bool:
        with _connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM memberships m
                    JOIN workspaces w ON w.organization_id = m.organization_id
                    WHERE m.user_id = %s AND m.organization_id = %s AND w.id = %s
                    LIMIT 1
                    """,
                    (user_id, organization_id, workspace_id),
                )
                return cur.fetchone() is not None

    def consume_rate_limit(self, action: str, rate_key: str, max_attempts: int, window_seconds: int) -> bool:
        if max_attempts <= 0 or window_seconds <= 0:
            return False
        now = _now()
        with _connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT window_started_at, attempt_count FROM auth_rate_limits WHERE action=%s AND rate_key=%s FOR UPDATE",
                    (action, rate_key),
                )
                row = cur.fetchone()
                if row is None:
                    cur.execute(
                        "INSERT INTO auth_rate_limits(action,rate_key,window_started_at,attempt_count) VALUES(%s,%s,%s,1)",
                        (action, rate_key, now),
                    )
                    conn.commit()
                    return True
                started = _as_utc(row[0])
                if (now - started).total_seconds() >= window_seconds:
                    cur.execute(
                        "UPDATE auth_rate_limits SET window_started_at=%s, attempt_count=1 WHERE action=%s AND rate_key=%s",
                        (now, action, rate_key),
                    )
                    conn.commit()
                    return True
                if int(row[1]) >= max_attempts:
                    conn.rollback()
                    return False
                cur.execute(
                    "UPDATE auth_rate_limits SET attempt_count=attempt_count+1 WHERE action=%s AND rate_key=%s",
                    (action, rate_key),
                )
            conn.commit()
            return True

    def record_security_event(
        self,
        event_type: str,
        *,
        email_hash: str | None,
        client_ip_hash: str | None,
        user_id: str | None,
        metadata: dict[str, str] | None,
    ) -> None:
        import uuid

        with _connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO security_events(id,event_type,created_at,user_id,email_hash,client_ip_hash,metadata_json)
                    VALUES(%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        uuid.uuid4().hex,
                        event_type,
                        _now(),
                        user_id,
                        email_hash,
                        client_ip_hash,
                        _json_adapter(metadata or {}),
                    ),
                )
            conn.commit()

    def list_security_events(self) -> list[dict[str, object]]:
        with _connect(self.database_url) as conn:
            with conn.cursor(row_factory=_dict_row_factory()) as cur:
                cur.execute(
                    """
                    SELECT id,event_type,created_at,user_id,email_hash,client_ip_hash,metadata_json
                    FROM security_events ORDER BY created_at ASC, id ASC
                    """
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]


def _json_adapter(value: Any) -> Any:
    try:
        from psycopg.types.json import Json
    except ImportError as exc:
        raise AuthPersistenceError("psycopg is required for PostgreSQL JSONB metadata.") from exc
    return Json(value)


def _dict_row_factory():
    try:
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise AuthPersistenceError("psycopg is required for PostgreSQL authentication persistence.") from exc
    return dict_row


def _as_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
