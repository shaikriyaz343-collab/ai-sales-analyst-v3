# V4 C3-E — Production Migration Rehearsal

## Purpose

C3-E validates the operational migration procedure on disposable state before any production cutover.

## State lifecycle

```text
Disposable SQLite source
        ↓
seed real auth state
        ↓
rollback snapshot
        ↓
migration
        ↓
verification
        ↓
external-mode target readiness
```

## Safety invariants

1. No production environment is permitted.
2. PostgreSQL rehearsal requires an explicit rehearsal URL.
3. The rehearsal URL must match the environment variable exactly.
4. No plaintext password or session token is exported by the rehearsal.
5. The SQLite rollback snapshot is created and verified before the temporary rehearsal workspace is cleaned up.
6. Production cutover remains a separate operation.

## Success criteria

- all auth tables are present
- representative users/organizations/memberships/workspaces/sessions/events/rate limits are created
- migration completes
- source/target critical fields verify equal
- rollback snapshot exists
- external PostgreSQL adapter can use the migrated schema in a disposable environment

## Not covered

This phase does not execute against customer production data and does not change the application's production persistence mode.
