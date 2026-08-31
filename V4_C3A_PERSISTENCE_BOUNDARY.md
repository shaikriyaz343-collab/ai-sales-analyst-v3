# V4 C3-A — Production Persistence Boundary

## Goal

C3-A establishes a provider-neutral persistence boundary without pretending the application has already been migrated to a production database or object store.

## Invariants

1. Analytical services do not need to know the eventual database/object-storage vendor.
2. Development/test persistence remains available through an explicit local adapter.
3. Production configuration cannot silently fall back to local runtime storage.
4. Dataset objects and JSON metadata are represented through persistence interfaces.
5. Session, monitoring, and saved-intelligence documents have separate persistence domains.
6. Persistence keys cannot escape their configured root in the local adapter.

## Modes

`V4_PERSISTENCE_MODE=local` is the development/test compatibility mode.

`V4_PERSISTENCE_MODE=external` is reserved for the C3-B production adapter. C3-A intentionally fails closed when this mode is selected rather than writing customer data to local disk.

## Architecture

```text
Analytical services
        |
        v
Persistence interfaces
   |             |
   v             v
Local adapter   C3-B external adapter
filesystem      DB + object storage
```

C3-A does not select a cloud/database vendor. That is intentionally deferred to C3-B.

## Validation

- Existing V4 tests remain unchanged.
- Persistence contract tests cover isolation between resource domains, path traversal rejection, local round trips, and production fail-closed behavior.
- Full backend regression, frontend production build, and browser acceptance remain release gates.
