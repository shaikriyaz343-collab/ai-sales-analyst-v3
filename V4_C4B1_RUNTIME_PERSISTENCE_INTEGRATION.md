# V4 C4-B1 — Runtime Persistence Integration

C4-B1 routes application-service document/object persistence through the existing
configured `PersistenceContext`.

It deliberately does not change:

- authentication/provider selection
- PostgreSQL connection pooling
- readiness/liveness
- observability
- backups
- deployment automation

Apply from the repository root:

```powershell
python .\APPLY_C4B1.py
```

The installer validates all expected source patterns first and only then writes
the complete change set transactionally. It preserves existing file bytes outside
the exact replacements.

First validation:

```powershell
python -m pytest tests_v4_saas/test_runtime_persistence_c4b1.py -q
```
