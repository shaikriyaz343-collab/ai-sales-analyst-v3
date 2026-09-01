# V4 C3-F — Real PostgreSQL Migration Rehearsal

## Purpose

C3-F exercises the actual PostgreSQL adapter and the SQLite-to-PostgreSQL migration against a disposable PostgreSQL instance.

It is intentionally not a production deployment procedure.

## Safety

- The rehearsal refuses to run when `V4_ENVIRONMENT=production`.
- The database URL must exactly match `V4_REHEARSAL_DATABASE_URL`.
- The supplied Docker Compose database is isolated on host port `55432`.
- The rehearsal creates representative auth state in a temporary SQLite database.
- The rehearsal validates migration before checking PostgreSQL auth behavior.
- No production database URL should ever be used with this package.

## Windows / Docker path

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File ".\RUN_C3F_POSTGRES_REHEARSAL.ps1"
```

The script starts:

```text
PostgreSQL 16
127.0.0.1:55432
database: v4_auth_rehearsal
user: v4_rehearsal
```

It then runs the real integration test and direct rehearsal.

Remove the disposable database afterward:

```powershell
docker compose -f docker-compose.c3f.yml down -v
```

## What is verified

- migration source/target equality for all seven auth tables
- PBKDF2 password hash compatibility
- migrated active session authentication
- organization/workspace isolation
- session revocation
- security-event history
- PostgreSQL rate limiting
- production-mode refusal

## Expected output

```text
C3-F PostgreSQL rehearsal: PASS
...
password hash: verified
active session: verified
tenant isolation: verified
revocation: verified
security events: verified
rate limits: verified
```

## Important

C3-F is complete only as a rehearsal when the disposable PostgreSQL run passes.

It does not switch the application to production `V4_PERSISTENCE_MODE=external`, and it does not perform a production migration.
