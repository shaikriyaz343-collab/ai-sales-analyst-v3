# V4 C4-F â€” Deployment / Production Rehearsal

## Purpose

C4-F defines and rehearses the deployment contract for the V4 SaaS
application. It does not introduce a cloud-specific deployment architecture.

The application topology is:

Browser
    |
    +-- HTTPS --> Next.js frontend
    |
    +-- HTTPS, credentialed API requests --> FastAPI backend
                                             |
                                             +-- PostgreSQL
                                             |
                                             +-- S3-compatible object storage

The frontend and backend remain separately addressable services. The frontend
uses `NEXT_PUBLIC_API_BASE_URL` to reach the FastAPI service.

## Application process

Start the V4 backend from the repository root:

```text
python -m backend.run_production
```

The production runner:

- starts `backend.api.main:app`;
- runs without Uvicorn reload mode;
- does not install dependencies;
- does not provision infrastructure;
- receives bind configuration from environment variables.

Optional process settings:

```text
V4_BIND_HOST=127.0.0.1
V4_BIND_PORT=8000
```

C4-F treats this as the application process entrypoint, not as a complete
deployment platform.

## Frontend configuration

The production frontend is built with:

```text
NEXT_PUBLIC_API_BASE_URL=https://api.example.com
```

The public frontend URL is independently supplied to deployed browser QA as
`APP_URL`.

The production backend must allow the frontend origin through
`V4_FRONTEND_ORIGINS` and must use the configured secure `__Host-` authentication
cookie contract.

## Production configuration

Production continues to use the existing authoritative configuration layer in
`backend/api/config.py`.

Required production identity/security settings include:

```text
V4_ENVIRONMENT=production
V4_RUNTIME_ROOT=...
V4_FRONTEND_ORIGINS=https://app.example.com
V4_TRUSTED_HOSTS=api.example.com
V4_AUTH_SECURE_COOKIE=true
V4_AUTH_COOKIE_NAME=__Host-v4_auth_session
```

External persistence additionally requires:

```text
V4_PERSISTENCE_MODE=external
V4_DATABASE_URL=...
V4_OBJECT_STORE_BUCKET=...
V4_OBJECT_STORE_REGION=...
```

The production configuration requires PostgreSQL TLS and HTTPS for custom
object-store endpoints, and rejects incomplete static object-store
credentials and unsafe object-store prefixes.

Do not commit production secrets or environment files.

## Durable state

The V4 external persistence model is:

PostgreSQL:

- authentication;
- organizations, memberships and workspaces;
- dataset/session/monitoring/saved-intelligence documents.

Object storage:

- uploaded dataset files.

The application must never fall back to local runtime storage when external
persistence is selected.

## Health and readiness

Liveness:

```text
GET /api/v1/health
```

Readiness:

```text
GET /api/v1/ready
```

`/health` is a lightweight liveness endpoint.

`/ready` indicates whether the application instance is safe to receive traffic.
When external persistence is enabled, PostgreSQL provider failure must make
readiness fail.

## Current evidence

The following application-side gates have been exercised successfully:

- C3-F real PostgreSQL migration rehearsal: PASS.
- C4-E2a external data-plane harness: 6/6 passed.
- Full `tests_v4_saas` suite with the rehearsal PostgreSQL database active:
  253 passed.
- Existing S3 adapter regression: 3 passed.
- Frontend production build: PASS.
- V4 browser acceptance: 7/7 passed.
- Non-reload FastAPI process runner: locally exercised with `/health` and
  `/ready` returning HTTP 200.

These results prove the V4 application-side external persistence contract with
real PostgreSQL and an injected S3 test client. They do not constitute a
production deployment approval.

## Remaining C4-F gates

The following remain outside the completed evidence above:

1. Exercise the production S3 adapter against a real networked S3-compatible
   object store.
2. Deploy the frontend and backend to a real staging/production-like
   environment.
3. Exercise restart and durable-state recovery in that deployed environment.
4. Validate production secret/environment injection and HTTPS endpoints.
5. Run the deployed browser acceptance suite against the deployed frontend.
6. Establish the deployment/rollback procedure for the selected platform.

C4-F is complete only after the applicable real-infrastructure rehearsal
passes.

No cloud provider, container platform, Kubernetes architecture, distributed
worker system, Redis limiter, or background-job architecture is required merely
to establish this application contract.

## Release validation

Before a deployment checkpoint:

```text
python -m pytest -q tests_v4_saas
cd frontend
npm.cmd run build
```

For deployed browser acceptance, the existing GitHub workflow uses the
repository variable `APP_URL` and runs the Playwright suite against the
already-deployed application.

The deployment system is responsible for supplying:

- a public HTTPS frontend URL;
- a public HTTPS API URL;
- the production environment variables and secrets;
- external PostgreSQL;
- S3-compatible object storage;
- process restart and rollback behavior.

The application remains responsible for its own configuration validation,
health/readiness behavior, authentication, tenant isolation, persistence
routing, and graceful lifecycle.