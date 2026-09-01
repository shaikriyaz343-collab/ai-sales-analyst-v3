# V4 C3-C — Authentication Persistence Migration

## Purpose

Move the V4 authentication authority from the development SQLite database to the production PostgreSQL database while preserving all existing authentication and C2 session-security semantics.

## Scope

C3-C includes:

- PostgreSQL authentication schema and runtime adapter.
- External-mode routing in `backend/api/services/auth.py`.
- Transactional SQLite → PostgreSQL migration tooling.
- Migration integrity verification.
- Compatibility with pre-C2 SQLite session tables (defaults `revoked_at` to NULL).
- Tests for IDs, password hashes, sessions, rate limits, security events, idempotency, rollback/verification, and external-mode routing.

C3-C does **not** perform a live production migration and does not remove SQLite support for development/test mode.

## Production authority

When `V4_PERSISTENCE_MODE=external`, authentication uses `V4_DATABASE_URL` for:

- organizations
- users
- memberships
- workspaces
- auth_sessions
- auth_rate_limits
- security_events

Analytical persistence remains governed by the C3-B persistence layer.

## Passwords and sessions

Password hashes are copied verbatim; users are not reset. Session tokens are not stored in plaintext and are not required for migration. Only the existing `token_hash` and session timestamps/revocation state are migrated.

C2 invariants remain enforced:

- revoked sessions remain unusable;
- absolute expiry is preserved;
- idle timeout is preserved;
- activity updates `last_seen_at` without extending `expires_at`.

## Migration command

Dry-run:

    python -m backend.api.migrations.auth_sqlite_to_postgres \
      --source "C:\\path\\to\\auth.db" \
      --database-url "postgresql://..." \
      --dry-run

Live import with verification:

    python -m backend.api.migrations.auth_sqlite_to_postgres \
      --source "C:\\path\\to\\auth.db" \
      --database-url "postgresql://..."

The migration is transactional. Existing identical rows are tolerated, but conflicting data is detected during verification rather than overwritten. The original SQLite database is never modified.

## Recommended cutover sequence

1. Stop auth writes or put the application into a maintenance/read-only window.
2. Run the dry-run.
3. Run the verified migration against PostgreSQL.
4. Confirm row counts and critical-field verification for every auth table.
5. Enable `V4_PERSISTENCE_MODE=external` with the production database URL.
6. Run post-cutover authentication smoke tests.
7. Retain the SQLite snapshot until the operational verification window is complete.

## Rollback

Before PostgreSQL accepts new writes, disable external mode and continue with SQLite.

After PostgreSQL has accepted new writes, the old SQLite snapshot is not a zero-loss rollback target. A reverse migration or point-in-time restoration procedure is required.

## Validation

The C3-C implementation was validated against the reconstructed C3-B repository with the complete backend suite:

    170 passed

Frontend production build and Playwright acceptance must still be run against the user's actual Windows repository after applying the replacement files.
