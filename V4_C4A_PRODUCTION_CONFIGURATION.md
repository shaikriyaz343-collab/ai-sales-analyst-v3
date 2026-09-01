# V4 C4-A — Production Configuration Hardening

C4-A hardens production configuration while leaving readiness, pooling,
observability, backups, and deployment automation for later C4 phases.

## Guarantees

- Production must use external persistence.
- Production database URLs must be PostgreSQL and explicitly enable TLS.
- Custom object-store endpoints must use HTTPS in production.
- Object-store static credentials must be supplied as a pair.
- Object-store prefixes cannot contain parent-directory path segments.
- Secret-bearing Settings fields are excluded from dataclass `repr` output.
- Existing local/test defaults remain unchanged.

## Validation

```powershell
python -m pytest tests_v4_saas/test_config_c4a.py -q
```

Then run the normal full backend, frontend build, and Playwright gates.
