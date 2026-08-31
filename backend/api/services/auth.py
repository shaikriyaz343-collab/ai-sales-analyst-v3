from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from ..config import settings

AUTH_STORAGE = settings.auth_storage
AUTH_DB = AUTH_STORAGE / "auth.db"
SESSION_COOKIE = settings.cookie_name
SESSION_TTL_DAYS = 7
PASSWORD_ITERATIONS = 310_000

LOGIN_RATE_LIMIT_IP = settings.auth_login_ip_limit
LOGIN_RATE_LIMIT_EMAIL = settings.auth_login_email_limit
LOGIN_RATE_LIMIT_WINDOW = settings.auth_login_window_seconds
SIGNUP_RATE_LIMIT_IP = settings.auth_signup_ip_limit
SIGNUP_RATE_LIMIT_EMAIL = settings.auth_signup_email_limit
SIGNUP_RATE_LIMIT_WINDOW = settings.auth_signup_window_seconds


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    name: str
    organization_id: str
    organization_name: str
    role: str
    workspace_id: str
    workspace_name: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _connect() -> sqlite3.Connection:
    AUTH_STORAGE.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUTH_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memberships (
                user_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (user_id, organization_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                UNIQUE (organization_id, name)
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS auth_rate_limits (
                action TEXT NOT NULL,
                rate_key TEXT NOT NULL,
                window_started_at TEXT NOT NULL,
                attempt_count INTEGER NOT NULL,
                PRIMARY KEY (action, rate_key)
            );
            CREATE TABLE IF NOT EXISTS security_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                user_id TEXT,
                email_hash TEXT,
                client_ip_hash TEXT,
                metadata_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memberships_org ON memberships(organization_id);
            CREATE INDEX IF NOT EXISTS idx_workspaces_org ON workspaces(organization_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON auth_sessions(token_hash);
            CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at);
            """
        )
        # Remove expired sessions opportunistically.
        conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (_iso(_utc_now()),))


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def consume_rate_limit(action: str, rate_key: str, max_attempts: int, window_seconds: int) -> bool:
    """Atomically consume one attempt from a SQLite-backed fixed window."""
    if max_attempts <= 0 or window_seconds <= 0:
        return False
    now = _utc_now()
    now_iso = _iso(now)
    with _connect() as conn:
        row = conn.execute(
            "SELECT window_started_at, attempt_count FROM auth_rate_limits WHERE action = ? AND rate_key = ?",
            (action, rate_key),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO auth_rate_limits(action,rate_key,window_started_at,attempt_count) VALUES(?,?,?,1)",
                (action, rate_key, now_iso),
            )
            return True
        try:
            started = datetime.fromisoformat(row["window_started_at"].replace("Z", "+00:00"))
        except ValueError:
            started = now
        if (now - started).total_seconds() >= window_seconds:
            conn.execute(
                "UPDATE auth_rate_limits SET window_started_at = ?, attempt_count = 1 WHERE action = ? AND rate_key = ?",
                (now_iso, action, rate_key),
            )
            return True
        if int(row["attempt_count"]) >= max_attempts:
            return False
        conn.execute(
            "UPDATE auth_rate_limits SET attempt_count = attempt_count + 1 WHERE action = ? AND rate_key = ?",
            (action, rate_key),
        )
        return True


def record_security_event(
    event_type: str,
    *,
    email: str | None = None,
    client_ip: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> None:
    """Persist authentication events without storing passwords, tokens, or raw identifiers."""
    init_db()
    metadata_json = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO security_events(
                id,event_type,created_at,user_id,email_hash,client_ip_hash,metadata_json
            ) VALUES(?,?,?,?,?,?,?)
            """,
            (
                uuid.uuid4().hex,
                event_type,
                _iso(_utc_now()),
                user_id,
                _stable_hash(_normalize_email(email)) if email else None,
                _stable_hash(client_ip) if client_ip else None,
                metadata_json,
            ),
        )


def _rate_key(prefix: str, value: str) -> str:
    return f"{prefix}:{_stable_hash(value)}"


def _validate_credentials(email: str, password: str, name: str | None = None) -> tuple[str, str]:
    email = _normalize_email(email)
    password = password or ""
    if "@" not in email or len(email) > 254:
        raise ValueError("Enter a valid email address.")
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters.")
    if name is not None and not name.strip():
        raise ValueError("Name is required.")
    return email, password


def create_account(email: str, password: str, name: str, organization_name: str) -> Principal:
    email, password = _validate_credentials(email, password, name)
    organization_name = organization_name.strip() or "My Organization"
    now = _iso(_utc_now())
    user_id = uuid.uuid4().hex
    org_id = uuid.uuid4().hex
    workspace_id = uuid.uuid4().hex
    workspace_name = "Main Workspace"
    with _connect() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise ValueError("An account with that email already exists.")
        conn.execute("INSERT INTO users(id,email,name,password_hash,created_at) VALUES(?,?,?,?,?)", (user_id, email, name.strip(), _hash_password(password), now))
        conn.execute("INSERT INTO organizations(id,name,created_at) VALUES(?,?,?)", (org_id, organization_name, now))
        conn.execute("INSERT INTO memberships(user_id,organization_id,role,created_at) VALUES(?,?,?,?)", (user_id, org_id, "owner", now))
        conn.execute("INSERT INTO workspaces(id,organization_id,name,created_at) VALUES(?,?,?,?)", (workspace_id, org_id, workspace_name, now))
    return Principal(user_id, email, name.strip(), org_id, organization_name, "owner", workspace_id, workspace_name)


def authenticate(email: str, password: str) -> Principal:
    email, password = _validate_credentials(email, password)
    init_db()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT u.id user_id, u.email, u.name, u.password_hash,
                   o.id organization_id, o.name organization_name,
                   m.role, w.id workspace_id, w.name workspace_name
            FROM users u
            JOIN memberships m ON m.user_id = u.id
            JOIN organizations o ON o.id = m.organization_id
            JOIN workspaces w ON w.organization_id = o.id
            WHERE u.email = ?
            ORDER BY w.created_at ASC
            LIMIT 1
            """,
            (email,),
        ).fetchone()
        if not row or not _verify_password(password, row["password_hash"]):
            raise ValueError("Email or password is incorrect.")
        return Principal(row["user_id"], row["email"], row["name"], row["organization_id"], row["organization_name"], row["role"], row["workspace_id"], row["workspace_name"])


def issue_session(user_id: str) -> tuple[str, datetime]:
    init_db()
    token = secrets.token_urlsafe(48)
    now = _utc_now()
    expires = now + timedelta(days=SESSION_TTL_DAYS)
    with _connect() as conn:
        conn.execute("INSERT INTO auth_sessions(id,user_id,token_hash,expires_at,created_at,last_seen_at) VALUES(?,?,?,?,?,?)", (uuid.uuid4().hex, user_id, _token_hash(token), _iso(expires), _iso(now), _iso(now)))
    return token, expires


def revoke_session(token: str | None) -> None:
    if not token:
        return
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_token_hash(token),))


def principal_from_token(token: str | None) -> Principal | None:
    if not token:
        return None
    init_db()
    now = _iso(_utc_now())
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT u.id user_id, u.email, u.name,
                   o.id organization_id, o.name organization_name,
                   m.role, w.id workspace_id, w.name workspace_name,
                   s.expires_at, s.id session_id
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            JOIN memberships m ON m.user_id = u.id
            JOIN organizations o ON o.id = m.organization_id
            JOIN workspaces w ON w.organization_id = o.id
            WHERE s.token_hash = ? AND s.expires_at > ?
            ORDER BY w.created_at ASC
            LIMIT 1
            """,
            (_token_hash(token), now),
        ).fetchone()
        if not row:
            return None
        conn.execute("UPDATE auth_sessions SET last_seen_at = ? WHERE id = ?", (now, row["session_id"]))
        return Principal(row["user_id"], row["email"], row["name"], row["organization_id"], row["organization_name"], row["role"], row["workspace_id"], row["workspace_name"])


def list_workspaces(organization_id: str) -> list[dict[str, str]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT id,name FROM workspaces WHERE organization_id = ? ORDER BY created_at ASC", (organization_id,)).fetchall()
        return [{"id": row["id"], "name": row["name"]} for row in rows]


def create_workspace(organization_id: str, name: str) -> dict[str, str]:
    name = name.strip()
    if not name or len(name) > 80:
        raise ValueError("Workspace name must be between 1 and 80 characters.")
    now = _iso(_utc_now())
    workspace = {"id": uuid.uuid4().hex, "name": name}
    try:
        with _connect() as conn:
            conn.execute("INSERT INTO workspaces(id,organization_id,name,created_at) VALUES(?,?,?,?)", (workspace["id"], organization_id, workspace["name"], now))
    except sqlite3.IntegrityError:
        raise ValueError("A workspace with that name already exists.")
    return workspace


def user_can_access_workspace(user_id: str, organization_id: str, workspace_id: str) -> bool:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM memberships m
            JOIN workspaces w ON w.organization_id = m.organization_id
            WHERE m.user_id = ? AND m.organization_id = ? AND w.id = ?
            LIMIT 1
            """,
            (user_id, organization_id, workspace_id),
        ).fetchone()
        return bool(row)


def principal_workspaces(principal: Principal) -> list[dict[str, str]]:
    return list_workspaces(principal.organization_id)


init_db()

def list_security_events() -> list[dict[str, object]]:
    """Return persisted authentication security events for operational diagnostics/tests."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, event_type, created_at, user_id, email_hash, client_ip_hash, metadata_json
            FROM security_events
            ORDER BY created_at ASC, id ASC
            """
        ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "created_at": row["created_at"],
                "user_id": row["user_id"],
                "email_hash": row["email_hash"],
                "client_ip_hash": row["client_ip_hash"],
                "metadata_json": row["metadata_json"],
            }
            for row in rows
        ]
