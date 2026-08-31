# V4 Production Configuration — Phase A

This phase adds a single typed configuration layer without changing analytical behavior.

## Files

- `backend/api/config.py` — authoritative environment/config parsing and production safety validation.
- `backend/api/main.py` — consumes configuration for CORS, trusted hosts, and auth cookie settings.
- `backend/api/services/auth.py` — consumes configured auth storage and cookie name.
- `backend/api/services/onboarding.py` — consumes configured dataset storage.
- `tests_v4_saas/test_config.py` — verifies development defaults and production fail-closed rules.

## Runtime environments

`V4_ENVIRONMENT` accepts:

- `development`
- `test`
- `staging`
- `production`

Development defaults preserve the current localhost behavior so the existing local V4 workflow is not disrupted.

## Production requirements

Production startup requires:

- `V4_RUNTIME_ROOT`
- `V4_FRONTEND_ORIGINS` with HTTPS origins only
- `V4_TRUSTED_HOSTS` without loopback hosts
- `V4_AUTH_SECURE_COOKIE=true`
- `V4_AUTH_COOKIE_NAME` beginning with `__Host-`

Optional settings include:

- `V4_AUTH_STORAGE`
- `V4_DATA_STORAGE`
- `V4_UPLOAD_MAX_BYTES` (default 50 MiB)

The upload limit is configured in Phase A but is not yet enforced by the upload service. Enforcement is a separate Phase D change.

## Example production environment

```text
V4_ENVIRONMENT=production
V4_RUNTIME_ROOT=/srv/ai-sales-analyst
V4_FRONTEND_ORIGINS=https://app.example.com
V4_TRUSTED_HOSTS=api.example.com
V4_AUTH_SECURE_COOKIE=true
V4_AUTH_COOKIE_NAME=__Host-v4_auth_session
V4_UPLOAD_MAX_BYTES=52428800
```

Do not commit real production secrets or environment files.

## Validation performed before handoff

```text
backend/api/config.py              py_compile: PASS
backend/api/main.py               py_compile: PASS
backend/api/services/auth.py      py_compile: PASS
backend/api/services/onboarding.py py_compile: PASS
tests_v4_saas/test_config.py      6 passed
```

The full V4 regression suite, frontend build, and Playwright 7-test gate must be re-run on the acceptance-green Windows checkout after these files are applied.
