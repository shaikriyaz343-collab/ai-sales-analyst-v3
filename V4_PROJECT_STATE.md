# AI Sales Analyst V4 — Engineering Handoff

## Current branch

v4/saas-foundation

## Current checkpoint

Commit:
e5ed122

Tag:
No tag created for C4-F deployment foundation yet.

Previous protected baseline:
c1c825f
v4-phase-c4e2e2-analysis-capacity-guard

## Completed phases

C4-D4a
- Request correlation
- Structured logging

C4-D4b
- Vendor-neutral operational metrics

C4-E1
- External runtime correctness
- Error boundary hardening
- Upload size enforcement
- S3 404/outage semantics
- Import-time external auth lifecycle correction

C4-E2b
- Atomic external materialization
- Unique temporary staging paths
- Concurrent download protection

C4-E2c
- Local staging before S3 upload
- Eliminated redundant S3 download after upload

C4-E2d
- Disposable bounded cache
- V4_CACHE_MAX_BYTES
- Recency-based eviction
- Startup orphan .tmp cleanup
- V4_CACHE_MAX_BYTES >= V4_UPLOAD_MAX_BYTES invariant

C4-E2e-1
- Analytical DataFrame loaded once
- profile_dataframe(data)
- /health converted to async
- /ready intentionally remains synchronous

C4-E2e-2
- V4_ANALYTICS_CONCURRENCY=4
- Process-local anyio.CapacityLimiter
- Created during FastAPI lifespan
- acquire_nowait()
- exhausted capacity -> HTTP 503
- /health and /ready remain outside limiter

C4-F deployment foundation
- Production FastAPI process entrypoint: python -m backend.run_production
- Non-reload Uvicorn process configuration
- Current C4-F deployment/rehearsal contract documented in V4_C4F_DEPLOYMENT.md
- C4-F production-runner tests

## Verified regression and build gates

Current full V4 backend/regression suite:

253 passed

Current C4-F deployment tests:

3 passed

Frontend production build:

PASS

V4 Playwright browser acceptance:

7 passed

The repository's deployed-URL browser workflow remains the browser gate for
an externally deployed application.

## Real external persistence rehearsal

### PostgreSQL

Real disposable PostgreSQL rehearsal database:

v4_auth_rehearsal

C3-F PostgreSQL rehearsal:

PASS

The external V4 suite was run with the rehearsal PostgreSQL database active.

### S3-compatible object storage

A disposable SeaweedFS 4.46 Windows AMD64 instance was used for local
networked S3-compatible rehearsal.

Endpoint:

http://127.0.0.1:8333

Bucket:

v4-s3-rehearsal

The real boto3 client was exercised against the network endpoint.

Verified:

- S3 bucket access
- object upload
- object HEAD
- object GET
- object DELETE
- V4 dataset upload through the real S3ObjectStore path
- V4 dataset retrieval through the real S3ObjectStore path
- object survival across SeaweedFS restart
- V4 authenticated Overview retrieval after the storage restart
- tenant isolation remained enforced

The rehearsal proves a real networked S3-compatible integration. It does
not prove AWS S3 or another eventual production object-store provider.

## V4 C4-F recovery evidence

The same dataset object survived SeaweedFS restart.

Dataset:

2cf8dcf61e2a40b9a489c93de0a4496f

Stored object:

v4/2cf8dcf61e2a40b9a489c93de0a4496f.csv

Recovered object size:

37 bytes

After storage restart, the V4 application successfully authenticated against
the external PostgreSQL auth store and successfully rebuilt the Overview from
the recovered S3-backed dataset.

Observed deterministic values included:

- pipeline_value = $300
- win_rate = 100%
- open pipeline value = $200

## Capacity evidence

V4_ANALYTICS_CONCURRENCY remains 4.

Prior E2e-3 measurements remain local, single-process Windows measurements.
They are not production or container capacity certification.

Current local evidence does not justify increasing the limiter to 8 or
lowering it to 2.

## Known limitations / remaining C4-F gates

The following remain unproven until a real deployed environment is exercised:

- production/staging deployment platform behavior
- real production object-storage provider integration
- production HTTPS endpoints
- production secret/environment injection
- deployed restart and durable-state recovery
- deployment rollback procedure
- final deployed Playwright acceptance
- Linux/container resource accounting and capacity behavior

The SeaweedFS rehearsal is S3-compatible integration evidence, not production
AWS S3 certification.

## Explicitly deferred

- Redis/distributed limiter
- Celery/background jobs
- process worker architecture
- DataFrame caching
- blanket async conversion
- Pandas chunking rewrite

These are not required merely to establish the current C4-F deployment
contract.

## Current working tree policy

Intentionally untracked:

- frontend/AGENTS.md
- frontend/CLAUDE.md

Generated/runtime artifacts must remain untracked, including local object-store
data, runtime caches, Playwright output, virtual environments, node_modules,
and .next.

## Next phase

C4-F real deployment / production rehearsal.

Priority:

1. select the real staging/deployment platform using current documented
   capabilities and costs
2. provision the minimum required staging infrastructure
3. configure external PostgreSQL and production-like S3 storage
4. configure HTTPS, secrets, environment variables and public frontend/API URLs
5. deploy the existing application without unnecessary architecture changes
6. exercise /health and /ready
7. exercise authentication and tenant isolation
8. exercise dataset persistence and object persistence
9. exercise restart/recovery
10. exercise failure behavior
11. exercise rollback
12. run deployed Playwright acceptance

## Checkpoint policy

Every meaningful V4 implementation, test, configuration, or authoritative
handoff-state change must be reviewed and validated before it is committed.

Generated runtime state, secrets, temporary investigation artifacts, and
unrelated local developer files must not be checkpointed.

C4-F is not production-approved until the applicable real infrastructure
rehearsal passes.
