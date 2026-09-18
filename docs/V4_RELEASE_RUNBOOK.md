# V4 Production Release and Rollback Runbook

## Purpose

This runbook turns the V4 release gate into a repeatable sequence. It separates repository validation from deployment-provider operations and requires evidence before a release is treated as certified.

## Operating model

V4 has exactly two participants:

- one human founder/operator
- the AI engineering agent

This is a deliberate constraint. Do not design release, support, QA, security, or incident procedures as though additional engineers, SREs, QA staff, security staff, or an on-call rotation exist.

The AI agent can execute technical work, tests, evidence collection, deployment orchestration, and incident analysis where connected tooling permits. The AI agent is not a second human approver, an independent separation-of-duties control, or a 24/7 human on-call role.

The human founder/operator retains responsibility for provider authorization, secrets, irreversible/high-impact changes, customer-impact decisions, incident decisions requiring human judgment, and final release/business acceptance.

Where conventional process would rely on team separation, compensate with automated gates, least-privilege access, immutable/reviewable evidence, deterministic checks, and explicit human approval.

## Release identity

Every release must record, at minimum:

- Git commit SHA deployed.
- Frontend build identifier/version, when the hosting platform exposes one.
- Backend deployment identifier/version, when the hosting platform exposes one.
- Deployment start and completion time.
- Environment name.
- Human production owner/approver.
- AI agent execution record, when applicable.
- Result of each release gate.

The deployed application must be traceable to the exact commit being certified. Historical browser or infrastructure evidence must not be reused for a different commit.

## Pre-release gates

1. Confirm the target branch and release commit.
2. Confirm the Python/runtime CI suite is green.
3. Confirm the frontend production build is green.
4. Confirm the high-severity npm audit finding is resolved or has an explicitly reviewed, time-bounded exception.
5. Confirm the release configuration contract is satisfied, including production environment selection, trusted hosts/origins, secure auth cookie settings, and external persistence configuration where required.
6. Confirm no secrets, runtime databases, object-store data, browser state, caches, or generated build artifacts are part of the release tree.
7. Confirm a rollback target is identified before deployment begins.

## Deployment sequence

1. Record the release identity and rollback target.
2. Deploy the exact release commit to the intended production/staging environment using the hosting provider's normal deployment mechanism.
3. Wait for the provider to report the deployment healthy.
4. Verify backend health/readiness through the deployed environment's operational checks. In external-persistence mode, readiness must reflect required PostgreSQL availability.
5. Verify the frontend is serving the deployed release.
6. Run Browser Acceptance QA against the deployed URL with `APP_URL` set to that deployment.
7. Verify the authenticated flow, tenant/workspace boundaries, dataset replacement semantics, deterministic analytical outputs, decision cockpit, forecast/scenario, Ask planning, action workflow, and monitoring surfaces covered by the release suite.
8. Record the exact browser run and deployment identifiers as release evidence.

A passing repository CI run is necessary but is not by itself proof that the deployed release is healthy.

## Post-deploy smoke checks

Immediately after release, verify:

- `/health` is responsive.
- `/ready` is healthy for the configured persistence mode.
- Sign-up/sign-in/session restoration and sign-out work.
- A workspace cannot read another organization's protected dataset/session state.
- User mutations remain scoped to the authenticated tenant/workspace/session.
- No production response exposes passwords, tokens, raw secrets, or unsanitized internal errors.
- Core analytical pages render for an authenticated workspace with a valid dataset.

## Monitoring and ownership

Because there is one human production owner, the release process must not imply staffed 24/7 coverage or an on-call rotation.

The human founder/operator owns the observation window and the decision to escalate, rollback, or authorize a provider action. The AI agent can inspect available signals, summarize incidents, prepare evidence, and execute reversible technical steps where tooling permits, but it is not itself continuous human monitoring coverage.

Track at minimum:

- Health/readiness failures.
- HTTP 5xx responses and authentication failures.
- Request latency on analytical endpoints.
- Analytics concurrency saturation relative to `V4_ANALYTICS_CONCURRENCY`.
- Database/persistence errors.
- Object-store persistence errors.
- Browser acceptance failures.
- Repeated tenant-isolation/security events.

The initial production thresholds must be configured from measured baseline behavior rather than guessed numeric limits. Until such measurements exist, record the signal, human owner, escalation path, and observation procedure without inventing thresholds.

## Rollback decision

Rollback is appropriate when a release causes a material regression in availability, correctness, authentication/authorization, tenant isolation, persistence integrity, or another release-blocking production invariant that cannot be safely corrected forward within the incident response window.

The human founder/operator is the decision owner for production rollback. The AI agent can prepare the rollback, verify deterministic checks, and collect evidence where tooling permits.

The incident record must contain:

- Incident start time.
- Affected deployment identifier.
- Observed failure and evidence.
- Human decision owner.
- AI execution/review record, when applicable.
- Rollback target.
- Customer/workspace impact, if known.
- Recovery confirmation.

## Rollback sequence

1. Freeze further production changes for the affected service.
2. Revert the frontend/backend deployment to the pre-recorded known-good release target using the deployment provider's rollback/redeploy mechanism.
3. Confirm deployment health and readiness.
4. Re-run the relevant browser acceptance and authenticated smoke checks.
5. Re-check tenant isolation and persistence integrity when the incident involved protected state or data access.
6. Confirm customer-facing behavior has returned to the known-good release.
7. Record the rollback deployment identifier and resulting commit/build identity.
8. Open a follow-up corrective action for the failed release rather than silently changing the production state again.

## Database and persistence safety

Application rollback must not assume that schema/data rollback is automatically safe. Before any migration-capable release:

- Identify whether the release changes persistent schema or stored data.
- Confirm the migration/recovery procedure for the provider and database in use.
- Avoid destructive migrations that cannot be recovered by the documented procedure.
- Treat object-store data and database state as production assets independent of the application deployment artifact.

## Dependency-failure rehearsal

Before final production approval, execute a controlled rehearsal in a non-production or explicitly isolated environment:

1. Select one real dependency failure mode, such as PostgreSQL or object storage becoming unavailable.
2. Confirm `/ready` and affected application behavior fail in the documented way.
3. Confirm unrelated health checks remain meaningful.
4. Restore the dependency.
5. Verify recovery without corrupting tenant or analytical state.
6. Record evidence and any remediation.

Do not perform destructive dependency testing against production unless the human founder/operator has explicitly authorized an isolated, reversible procedure.

## Release evidence record

For each certified release, retain:

- Exact commit SHA.
- CI run identifiers and outcomes.
- npm audit outcome.
- Deployment/provider identifiers.
- Human production owner.
- AI execution record, when applicable.
- Browser acceptance run identifier and result.
- Health/readiness result.
- Capacity/resource measurements.
- Dependency-failure rehearsal result.
- Restart/recovery result when performed.
- Tenant-isolation verification result.
- Rollback target and rollback test/rehearsal result.
- Any approved exceptions, owner, rationale, and expiry/review date.

## Current V4 status

This document defines the release choreography; it does not claim that the deployment-dependent gates are already satisfied. The current foundation still requires exact-release deployed browser evidence, Linux/container capacity certification, dependency-failure rehearsal, restart/recovery evidence, systematic post-promotion security review, cross-site auth architecture resolution, npm audit resolution/exception, and completed monitoring ownership before final production approval.
