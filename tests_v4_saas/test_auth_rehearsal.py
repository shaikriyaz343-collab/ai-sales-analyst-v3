from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.api.migrations.auth_rehearsal import create_rehearsal_source, run_memory_rehearsal


def test_rehearsal_creates_disposable_source_with_all_auth_tables(tmp_path: Path):
    source, material = create_rehearsal_source(tmp_path)

    assert source.exists()
    assert material["owner_user_id"]

    with sqlite3.connect(source) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert {
        "organizations",
        "users",
        "memberships",
        "workspaces",
        "auth_sessions",
        "auth_rate_limits",
        "security_events",
    } <= tables


def test_memory_rehearsal_verifies_every_auth_table():
    result = run_memory_rehearsal()

    assert result.verified_tables == (
        "organizations",
        "users",
        "memberships",
        "workspaces",
        "auth_sessions",
        "auth_rate_limits",
        "security_events",
    )
    assert result.source_counts == result.target_counts
    assert result.rollback_snapshot_created is True
