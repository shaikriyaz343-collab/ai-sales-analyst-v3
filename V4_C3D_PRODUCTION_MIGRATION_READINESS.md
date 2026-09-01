# V4 C3-D Production Migration Readiness

## Purpose

C3-D turns the C3-C authentication migration capability into an operator-safe production procedure.
It does not perform a live migration and does not change the production database.

## Safety contract

The migration command is now read-only unless `--apply` is explicitly supplied.

```powershell
python -m backend.api.migrations.auth_sqlite_to_postgres `
  --source PATH_TO_AUTH_DB `
  --database-url "$env:V4_DATABASE_URL"
```

The command above is a dry-run.

Actual writes require:

```powershell
python -m backend.api.migrations.auth_sqlite_to_postgres `
  --source PATH_TO_AUTH_DB `
  --database-url "$env:V4_DATABASE_URL" `
  --apply
```

## Preflight

```powershell
python -m backend.api.migrations.auth_preflight `
  --source PATH_TO_AUTH_DB `
  --database-url "$env:V4_DATABASE_URL" `
  --require-production
```

Preflight verifies the SQLite source, foreign-key integrity, source tables/counts, PostgreSQL reachability, and PostgreSQL auth schema availability.

## Cutover check

```powershell
python -m backend.api.migrations.auth_cutover_check `
  --database-url "$env:V4_DATABASE_URL"
```

This verifies that production is configured for external persistence and that the required authentication tables are available.

## Production sequence

1. Back up `auth.db`.
2. Freeze authentication writes.
3. Run preflight.
4. Prepare PostgreSQL schema.
5. Run dry-run.
6. Review source counts and operator output.
7. Run migration with `--apply`.
8. Verify the migration result.
9. Run cutover check.
10. Deploy the application with `V4_PERSISTENCE_MODE=external`.
11. Verify readiness and login/me/logout.
12. Verify tenant isolation and session revocation.
13. Preserve the original SQLite backup until the production verification window closes.

## Rollback

Before any PostgreSQL writes, aborting the process leaves SQLite authoritative.

After PostgreSQL starts accepting new writes, the old SQLite snapshot is no longer a lossless rollback source. Reverse migration or controlled restoration is required. Do not switch back blindly.

## Non-goals

C3-D does not migrate live customer data, does not remove SQLite support for development/test, and does not change password or session security semantics established in C1/C2.

## Acceptance gates

- migration command is safe-by-default
- preflight fails closed
- dry-run performs no writes
- migration remains transactional
- source/target integrity checks remain mandatory
- full backend regression remains green
- frontend build remains green
- Playwright remains 7/7
