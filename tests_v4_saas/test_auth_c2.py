from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

import backend.api.services.auth as auth


@pytest.fixture
def auth_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth, "AUTH_STORAGE", tmp_path / "auth")
    monkeypatch.setattr(auth, "AUTH_DB", tmp_path / "auth" / "auth.db")
    auth.init_db()
    return tmp_path / "auth" / "auth.db"


def _create_user() -> auth.Principal:
    return auth.create_account(
        "c2@example.com",
        "StrongPassword1!",
        "C2 User",
        "C2 Org",
    )


def test_active_session_authenticates(auth_db):
    principal = _create_user()
    token, _ = auth.issue_session(principal.user_id)

    restored = auth.principal_from_token(token)

    assert restored is not None
    assert restored.user_id == principal.user_id


def test_logout_revokes_session(auth_db):
    principal = _create_user()
    token, _ = auth.issue_session(principal.user_id)

    auth.revoke_session(token)

    assert auth.principal_from_token(token) is None

    with sqlite3.connect(auth.AUTH_DB) as conn:
        revoked = conn.execute(
            "SELECT revoked_at FROM auth_sessions WHERE token_hash = ?",
            (auth._token_hash(token),),
        ).fetchone()
    assert revoked is not None
    assert revoked[0] is not None


def test_idle_timeout_revokes_session(auth_db, monkeypatch):
    principal = _create_user()
    token, _ = auth.issue_session(principal.user_id)

    monkeypatch.setattr(auth, "SESSION_IDLE_SECONDS", 60)

    with sqlite3.connect(auth.AUTH_DB) as conn:
        conn.execute(
            "UPDATE auth_sessions SET last_seen_at = ? WHERE token_hash = ?",
            (
                auth._iso(auth._utc_now() - timedelta(seconds=61)),
                auth._token_hash(token),
            ),
        )

    assert auth.principal_from_token(token) is None

    with sqlite3.connect(auth.AUTH_DB) as conn:
        revoked = conn.execute(
            "SELECT revoked_at FROM auth_sessions WHERE token_hash = ?",
            (auth._token_hash(token),),
        ).fetchone()
    assert revoked[0] is not None


def test_activity_refreshes_last_seen_without_extending_absolute_expiry(
    auth_db,
    monkeypatch,
):
    principal = _create_user()
    token, expires = auth.issue_session(principal.user_id)

    monkeypatch.setattr(auth, "SESSION_IDLE_SECONDS", 3600)

    before = auth._utc_now()
    with sqlite3.connect(auth.AUTH_DB) as conn:
        row = conn.execute(
            "SELECT expires_at, last_seen_at FROM auth_sessions WHERE token_hash = ?",
            (auth._token_hash(token),),
        ).fetchone()

    original_expires = row[0]
    original_last_seen = row[1]

    restored = auth.principal_from_token(token)
    assert restored is not None

    with sqlite3.connect(auth.AUTH_DB) as conn:
        row = conn.execute(
            "SELECT expires_at, last_seen_at FROM auth_sessions WHERE token_hash = ?",
            (auth._token_hash(token),),
        ).fetchone()

    assert row[0] == original_expires
    assert row[1] >= original_last_seen
    assert datetime_from_iso(row[0]) == expires
    assert datetime_from_iso(row[0]) > before


def datetime_from_iso(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_absolute_expiry_rejects_session(auth_db, monkeypatch):
    principal = _create_user()
    token, _ = auth.issue_session(principal.user_id)

    with sqlite3.connect(auth.AUTH_DB) as conn:
        conn.execute(
            "UPDATE auth_sessions SET expires_at = ? WHERE token_hash = ?",
            (
                auth._iso(auth._utc_now() - timedelta(seconds=1)),
                auth._token_hash(token),
            ),
        )

    assert auth.principal_from_token(token) is None


def test_revoked_session_cannot_be_resurrected(auth_db):
    principal = _create_user()
    token, _ = auth.issue_session(principal.user_id)

    auth.revoke_session(token)
    assert auth.principal_from_token(token) is None

    with sqlite3.connect(auth.AUTH_DB) as conn:
        conn.execute(
            "UPDATE auth_sessions SET last_seen_at = ? WHERE token_hash = ?",
            (auth._iso(auth._utc_now()), auth._token_hash(token)),
        )

    assert auth.principal_from_token(token) is None


def test_revoke_all_sessions_revokes_every_session(auth_db):
    principal = _create_user()
    token_a, _ = auth.issue_session(principal.user_id)
    token_b, _ = auth.issue_session(principal.user_id)

    assert auth.principal_from_token(token_a) is not None
    assert auth.principal_from_token(token_b) is not None

    revoked = auth.revoke_all_sessions(principal.user_id)

    assert revoked == 2
    assert auth.principal_from_token(token_a) is None
    assert auth.principal_from_token(token_b) is None


def test_revoke_all_sessions_is_idempotent(auth_db):
    principal = _create_user()
    auth.issue_session(principal.user_id)

    assert auth.revoke_all_sessions(principal.user_id) == 1
    assert auth.revoke_all_sessions(principal.user_id) == 0


def test_c2_migrates_existing_auth_sessions_table(auth_db):
    # Recreate the legacy table shape in a fresh database.
    with sqlite3.connect(auth.AUTH_DB) as conn:
        conn.execute("DROP TABLE auth_sessions")
        conn.execute(
            """
            CREATE TABLE auth_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
            """
        )

    auth.init_db()

    with sqlite3.connect(auth.AUTH_DB) as conn:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(auth_sessions)").fetchall()
        }

    assert "revoked_at" in columns
