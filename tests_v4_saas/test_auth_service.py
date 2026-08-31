from __future__ import annotations

import os
from pathlib import Path

import pytest

import backend.api.services.auth as auth


@pytest.fixture
def auth_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth, "AUTH_STORAGE", tmp_path / "auth")
    monkeypatch.setattr(auth, "AUTH_DB", tmp_path / "auth" / "auth.db")
    auth.init_db()
    return tmp_path / "auth" / "auth.db"


def test_signup_creates_private_org_and_workspace(auth_db):
    principal = auth.create_account("owner@example.com", "StrongPassword1!", "Riyaz", "Acme")
    assert principal.role == "owner"
    assert principal.organization_name == "Acme"
    assert len(auth.list_workspaces(principal.organization_id)) == 1


def test_password_is_hashed_and_login_issues_session(auth_db):
    principal = auth.create_account("owner@example.com", "StrongPassword1!", "Riyaz", "Acme")
    token, expires = auth.issue_session(principal.user_id)
    assert token
    assert expires.tzinfo is not None
    restored = auth.principal_from_token(token)
    assert restored is not None
    assert restored.user_id == principal.user_id


def test_wrong_password_does_not_authenticate(auth_db):
    auth.create_account("owner@example.com", "StrongPassword1!", "Riyaz", "Acme")
    with pytest.raises(ValueError, match="incorrect"):
        auth.authenticate("owner@example.com", "WrongPassword1!")


def test_duplicate_email_is_rejected(auth_db):
    auth.create_account("owner@example.com", "StrongPassword1!", "Riyaz", "Acme")
    with pytest.raises(ValueError, match="already exists"):
        auth.create_account("OWNER@example.com", "StrongPassword2!", "Other", "Other")
