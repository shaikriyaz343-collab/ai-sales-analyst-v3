# V4 C2 — Session Security

## Purpose

C2 hardens the authenticated session lifecycle without replacing the existing V4 authentication model.

## Invariants

A session is usable only when:

1. The supplied token hashes to an existing session.
2. The session is not revoked.
3. The absolute session expiry has not passed.
4. The idle timeout has not passed since `last_seen_at`.

Successful authentication updates `last_seen_at` but never changes `expires_at`.

## Configuration

- `V4_AUTH_SESSION_IDLE_SECONDS=1800` — 30-minute idle timeout.
- `V4_AUTH_SESSION_MAX_SECONDS=604800` — 7-day absolute maximum lifetime.

The idle timeout must be strictly less than the absolute lifetime.

## Revocation

Logout marks the session with `revoked_at` rather than deleting it.

`revoke_all_sessions(user_id)` revokes every currently active session belonging to the user.

A revoked session cannot be resurrected by changing `last_seen_at`.

## Persistence migration

Existing `auth_sessions` tables are migrated in place by adding `revoked_at` when the column is absent. This avoids requiring existing development/staging databases to be recreated.

## Validation

C2 acceptance should include:

- active session authentication
- logout revocation
- idle timeout
- activity refresh
- absolute lifetime preservation
- absolute expiry
- revoked-session rejection
- revoke-all behavior
- idempotent revoke-all
- legacy database migration

The existing V4 SaaS acceptance suite remains a regression gate.
