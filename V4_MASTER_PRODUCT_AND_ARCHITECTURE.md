# V4 Master Product & Architecture Constitution

## 1. Product Vision

V4 is a monetized, multi-tenant SaaS AI Sales Analyst.

The customer experience should be highly automated: a customer creates an account, selects a plan, creates or enters a workspace, uploads sales data, and the application turns that data into useful business intelligence with minimal manual configuration.

The intended end-product is not a developer-facing analytics toolkit. It is a production SaaS application that customers can use, trust, pay for, and return to.

The customer-facing value proposition is:

> Upload sales data and get automated, trustworthy business intelligence.

The application is expected to automate the majority of the routine workflow while exposing important decisions, preserving customer control, and failing safely.

## 2. Target Customer Journey

Conceptually:

Customer
-> account creation/authentication
-> organization/tenant
-> plan/subscription
-> workspace
-> data upload
-> automatic ingestion and validation
-> profiling and schema/dimension discovery
-> analytical session
-> dashboard / executive report / interactive analysis
-> monitoring and alerts
-> saved intelligence
-> dataset replacement/refresh
-> ongoing use

Supporting SaaS capabilities include authentication, authorization, tenant isolation, billing, usage/entitlements, persistence, object storage, AI/analytics, monitoring, audit/security, health/readiness, backups, and deployment safety.

The customer should not need to understand Python, pandas, PostgreSQL, SQL, storage schemas, or model prompting in order to use the core product.

## 3. Automation Philosophy

Automate the routine.
Expose important decisions.
Fail safely.
Never silently corrupt customer data.

A typical upload should move through:

Upload
-> file/type validation
-> ingestion
-> profiling
-> schema/dimension discovery
-> problem detection
-> analytical representation
-> dataset/session creation
-> scope application
-> initial business insights
-> executive report
-> queryable analytical state
-> monitoring/alerts

Automation does not authorize silent semantic corruption. Inferred metadata may be surfaced for user confirmation where business meaning is ambiguous.

## 4. Product Architecture

Target production shape:

Customer
-> Next.js web application
-> FastAPI API
-> PostgreSQL (auth + durable application data)
-> Object storage (uploaded files and other durable binary artifacts)
-> External APIs/services

Core architectural rule:

> No production-critical state should depend on the application server's local filesystem.

Local development/test may use:
- SQLite
- local filesystem

Production must use external durable infrastructure and must fail closed rather than silently falling back to local disk.

The application should remain infrastructure-neutral. It should be deployable against compatible managed PostgreSQL/object storage on AWS, Azure, GCP, private infrastructure, or another environment without rewriting domain services.

## 5. Historical Engineering Progression

Persistence/authentication progression:

C3-A  Persistence boundary
C3-B  Production persistence adapters
C3-C  Authentication persistence migration
C3-D  Production migration readiness
C3-E  Disposable migration rehearsal
C3-F  Real PostgreSQL rehearsal

C3-F demonstrated the real PostgreSQL migration and auth behavior against the native PostgreSQL installation, including:
- migration
- timestamp normalization
- JSON/JSONB verification
- password hash verification
- active session verification
- tenant isolation
- session revocation
- security events
- rate limiting
- full backend validation
- frontend build
- Playwright acceptance

Important boundary:

> C3-F PASS does not equal production cutover.

C4 exists to harden the running application operationally.

## 6. C4 Mission

Authoritative C4 mission:

> Make the application safe and predictable when it is actually running as a production service.

Production dependency model:

Next.js
-> FastAPI
-> PostgreSQL / Object Store / External APIs

C4 is runtime hardening, not a deployment-specific rewrite.

## 7. C4 Capability Areas

### C4.1 Configuration and secrets
- Local, test, and production configuration classes
- Production external persistence required
- Missing production configuration causes startup/readiness failure
- No fallback to local disk
- Secret-bearing configuration audited

### C4.2 Secrets hygiene
Production secrets must never be:
- committed
- logged
- returned by health endpoints
- included in exception messages
- included in migration output
- included in test fixtures

Validation errors may identify a missing variable, but never expose its value.

### C4.3 PostgreSQL connection lifecycle
Required controls include:
- connection timeout
- statement timeout
- pool size
- pool acquisition timeout
- connection recycling
- health checking
- graceful close

Lifecycle:
application startup
-> initialize persistence
-> application ready

application shutdown
-> stop accepting work
-> close pools cleanly

### C4.4 Readiness and liveness
Liveness:
GET /api/v1/health
-> answers whether the process is alive
-> must be cheap and not dependent on every downstream system

Readiness:
GET /api/v1/ready
-> answers whether the instance can safely receive production traffic
-> external mode verifies required production dependencies sufficiently
-> PostgreSQL unavailable means not ready
-> no local fallback

### C4.5 Dependency failure behavior
Database unavailable:
- readiness fails
- critical requests fail safely
- no local fallback

Object storage:
- failure behavior is operation-aware
- uploads may fail clearly
- existing analytical metadata may remain readable when possible

Use dependency-aware failure policies instead of a blanket "everything is down" response.

### C4.6 Timeouts
Every external dependency must have bounded timeouts:
- database connect
- database statement
- object storage
- HTTP connect
- HTTP read

Avoid unbounded waits that can exhaust workers.

### C4.7 Error handling
Production responses distinguish:
- business errors
- validation errors
- authorization errors
- dependency failures
- unexpected internal errors

Do not expose database traces, hosts, usernames, database URLs, SQL, tokens, or other implementation details to clients. Dependency failures should normally become a safe response such as HTTP 503, while detailed diagnostics go to structured server logs.

### C4.8 Structured logging
Request-level logs should support:
- request_id
- timestamp
- method
- route
- status
- duration
- organization_id when safe
- user_id when safe

Never log passwords, session tokens, authorization headers, DATABASE_URL, or uploaded secrets.

Security/audit events remain a separate stream from ordinary application logs.

### C4.9 Correlation IDs
Support X-Request-ID or generated request IDs across:
request
-> route
-> service
-> persistence
-> dependency failure

without exposing customer secrets.

### C4.10 Metrics
Define observability for at least:
- request count
- request latency
- 5xx count
- authentication failures
- rate-limit hits
- database pool utilization
- database failures
- object-store failures
- migration status

This is a metrics contract, not a vendor decision.

### C4.11 Startup validation
Production startup should validate:
- environment
- persistence mode
- database configuration
- schema version
- auth persistence
- object storage
- security settings
- cookie configuration
- trusted hosts
- CORS configuration

Incompatible production configuration must prevent readiness.

### C4.12 Schema/version management
The runtime must know:
- application expected schema version
- database provided schema version

and reject incompatible combinations.

The production application must not rely on "the tables probably exist."

### C4.13 Graceful shutdown
Preferred sequence:
SIGTERM
-> stop accepting new traffic
-> finish active requests
-> close database pool
-> close external clients
-> exit

### C4.14 Backups
PostgreSQL backup contract:
- scheduled backups
- point-in-time recovery capability
- retention
- restore verification

Object storage backup contract:
- versioning where appropriate
- retention
- backup/replication strategy

Principle:

> A backup that has never been restored is an assumption, not a recovery strategy.

A restore rehearsal should be performed later.

Do not select a final cloud backup vendor prematurely.

### C4.15 Deployment safety
Deployment gates:
build
-> tests
-> schema compatibility
-> configuration validation
-> deploy
-> readiness
-> smoke test

A process merely starting does not mean the deployment is healthy.

### C4.16 Security baseline
Preserve prior:
- C1 abuse protection
- C2 session security
- C3 persistence security

Continue verifying:
- secure cookies
- trusted hosts
- CORS restrictions
- security headers
- rate limits
- session expiry
- session revocation
- tenant isolation

No security regression is acceptable because of runtime infrastructure changes.

### C4.17 Runtime tests
Dedicated C4 runtime test boundary should cover:
- configuration
- production startup validation
- readiness
- liveness
- database failure
- object-store failure
- timeouts
- connection lifecycle
- graceful shutdown
- request IDs
- error sanitization
- secret redaction
- schema compatibility

Global gates remain mandatory:
- all backend tests
- frontend production build
- Playwright 7/7

## 8. C4 Checkpoint Strategy

Authoritative roadmap capabilities:

C4-A  Production configuration + startup validation
C4-B  Database connection lifecycle + readiness
C4-C  Observability + error handling
C4-D  Deployment/runtime integration tests
C4-E  Backup/restore rehearsal
C4-F  Production deployment readiness

The repository's historical implementation checkpoints are finer-grained than the authoritative roadmap labels. For example, the repository contains executed checkpoints like:
- C4-B1: Runtime persistence integration
- C4-C: PostgreSQL connection-pool lifecycle

Note that the historical implementation sequence (like tagging the pool lifecycle as C4-C) does not perfectly match the roadmap lettering (where connection lifecycle is C4-B). Capability mapping matters more than renaming historical checkpoint tags and commits.

Current repository checkpoint:
76ada29
tag: v4-phase-c4c-postgresql-pool-lifecycle

This checkpoint contains the implemented PostgreSQL runtime connection-pool lifecycle and its validated integration.

## 9. Current C4-C Result

C4-C PostgreSQL connection-pool lifecycle was implemented and validated.

Validated evidence:
- focused C4-C tests: 6 passed
- C4-B1/component regression set: 49 passed
- full backend suite: 199 passed, 1 skipped
- frontend production build: passed
- V4 Playwright acceptance: 7/7 passed
- git diff --check: passed

Lifecycle properties established:
- external runtime does not lazily initialize before lifecycle startup
- lifecycle owns external provider startup
- shared provider reaches all four PostgreSQL JSON stores
- shared provider reaches PostgreSQL auth
- startup failures clean up
- auth/schema startup failure cleans up
- readiness failure is not double-close prone
- shutdown resets auth/runtime state before provider close
- later lifecycle gets fresh runtime state
- local SQLite behavior remains preserved
- migration/rehearsal direct connection paths remain independent

## 10. Critical Engineering Principles

1. Fail closed in production.
2. Never silently substitute local persistence for missing external infrastructure.
3. Treat tenant isolation as a hard security boundary.
4. Treat customer data durability as a product requirement.
5. Treat automation as the core user experience, not merely an implementation convenience.
6. Preserve existing contracts unless a change is intentional, documented, tested, and justified.
7. Never weaken a test merely to make an implementation green.
8. Prefer small coherent checkpoints over giant risky changes.
9. Use the repository and planning documents as the durable source of truth.
10. Do not use deployment-specific architecture when an infrastructure-neutral abstraction is possible.
11. Every externally visible failure must be safe and comprehensible.
12. Secrets never enter logs, responses, fixtures, commits, or diagnostics.
13. Operational correctness includes failure, recovery, upgrades, and shutdown—not only the happy path.
14. A green unit suite is necessary but insufficient; integration, build, browser acceptance, lifecycle, and operational validation all matter.
15. A backup is not proven until restoration is verified.
16. Do not confuse migration success with production cutover.
17. Do not confuse process startup with service readiness.
18. Prefer explicit resource ownership and lifecycle boundaries over hidden module side effects.

## 11. Working Method

For every meaningful phase/checkpoint:

AUTHORITATIVE SPEC
-> actual repository inspection
-> architecture review
-> smallest coherent implementation slice
-> targeted tests
-> regression tests
-> real integration tests
-> frontend build
-> Playwright acceptance
-> diff/security review
-> checkpoint commit
-> checkpoint tag

Do not create ad-hoc installer scripts for complex repository refactors when a repository-aware coding agent can work directly against the actual source.

When a coding agent is used:
- inspect before editing
- preserve known-good checkpoints
- use isolated worktrees/branches when practical
- never blindly apply another agent's partial implementation
- require explicit review before commit/tag
- do not let tests be weakened to satisfy the implementation

## 12. Agent Handoff / Chat-Limit Strategy

The repository should remain self-describing.

Important project decisions, roadmap milestones, architecture principles, checkpoint tags, and known failure lessons should be documented in version control.

This file is the durable project constitution and should be updated when a major architectural or product principle changes.

## 13. Monetization / SaaS Direction

The application is intended to be monetized.

The long-term product must therefore support, as appropriate:
- accounts
- organizations/tenants
- subscriptions/plans
- billing
- usage/entitlements
- authentication/authorization
- data lifecycle
- automated analytics
- monitoring/alerts
- customer supportability
- audit/security
- backup/recovery
- safe deployment/upgrade

Billing and entitlement logic should be introduced deliberately according to the product roadmap, not bolted onto unrelated infrastructure changes.

The product should optimize for:
customer value
+
trust
+
automation
+
operational reliability
+
security
+
recoverability
+
scalability
+
cost awareness

## 14. Known Lessons from This Build

Repeated failures occurred when complex multi-file refactors were attempted through brittle generated installers, exact-string replacement scripts, patch wrappers, or assumptions about source formatting.

Observed failure classes included:
- PowerShell parameter/quoting problems
- exact-match count mismatches
- AST indentation corruption
- Windows cp1252 decoding failures under Python 3.14
- silent no-op apply behavior
- incomplete/missing generated files
- tests that initially depended on an installed third-party package merely to test a wrapper

The corrective principle is:

> Prefer direct repository-aware implementation and Git-native review over custom patch/install machinery.

Codex and Gemini/Antigravity are appropriate repository-level coding agents. The coding agent should inspect, implement, test, and report. Architectural/product/release review remains an independent gate.

## 15. Current Safety Checkpoints

Known-good:
- C3-F real PostgreSQL rehearsal checkpoint: 112ee12
- C4-B1 runtime persistence integration checkpoint: eaedd26
- C4-C PostgreSQL pool lifecycle checkpoint: 76ada29

Current branch:
v4/saas-foundation

Current C4-C checkpoint:
76ada29

Historical partial Codex C4-C work is preserved in:
stash@{0}: C4-C partial Codex implementation backup

Keep that stash until a later checkpoint is stable.

## 16. CEO-Level Decision Framework

Every proposed change should be evaluated through five lenses:

Product:
Does this materially improve the customer experience or business viability?

Architecture:
Does it keep the system modular, tenant-safe, durable, infrastructure-neutral, and evolvable?

Operations:
Can we observe it, diagnose it, deploy it, shut it down, recover it, and upgrade it safely?

Security:
Does it preserve isolation, secret hygiene, authentication/session security, and fail-closed behavior?

Economics:
Can the resulting system scale at a sensible cost and support monetization/entitlements?

The objective is not to accumulate code or checkpoints.

The objective is to build a SaaS product that customers can trust enough to pay for.
