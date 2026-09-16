# AI Sales Analyst V4 — Deep Repository Audit

Date: 2026-09-16
Branch audited: `v4/saas-foundation`

## Purpose

This audit reconciles the actual promoted repository tree against milestone documents, tests, runtime code, release gates, and product architecture. It is intended to prevent already-cleared work from being repeated and to expose discrepancies between documentation and implementation.

## Cleared at repository level

- SaaS identity foundation: organizations, memberships, workspaces, authenticated sessions, session expiry/revocation, rate limiting, and protected API boundaries.
- External PostgreSQL runtime persistence and auth persistence integration.
- S3-compatible object storage adapter with bounded upload/cache handling and missing-vs-outage distinction.
- Production fail-closed configuration for external persistence, TLS requirements, secure cookies, trusted hosts, CORS, and security headers.
- Liveness/readiness endpoints and explicit runtime lifecycle ownership.
- Upload size enforcement, bounded reads, and failed-upload cleanup.
- Browser Acceptance QA workflow wiring on `v4/saas-foundation` with safe `APP_URL` handling.
- Release/rollback runbook documentation from merged PR #16.
- Turbopack workspace-root warning remediation.
- Core V4 product surfaces through Saved Intelligence.

## Current release gates that remain external or operational

- Exact deployed Playwright acceptance against the promoted release build.
- Linux/container resource and capacity certification.
- Controlled real dependency-failure rehearsal and restart/recovery evidence.
- Deployed tenant-isolation verification.
- Production cross-site cookie/domain validation.
- Measured monitoring thresholds and ownership.
- Production deployment/cutover evidence.

These gates must not be closed using historical evidence from an earlier tree.

## Dependency security finding

The current frontend lockfile contains `sharp` version `0.35.3`. The repository CI previously reported one high-severity npm audit finding. Public advisory data identifies `sharp` versions below `0.35.4` as affected by a high-severity libheif issue. The precise remediation must be validated by the repository's actual npm audit output before the release gate is closed.

## Correctness discrepancy found

The decision-signal documentation claimed that impact scoring preserved the actual signal kind, but the audited implementation still derived kind from severity inside `_impact_score`. This means a high-severity opportunity could be scored as a risk. The correction is isolated to `backend/api/services/decision_signals.py`, with a regression test covering a high-severity opportunity.

## Persistence/API failure contract observation

The S3 persistence adapter raises `PersistenceConfigurationError` for object-store outage/permission failures while the API explicitly maps `BotoCoreError` and `ClientError` to HTTP 503. The repository should align this boundary so configured persistence failures do not accidentally surface as generic HTTP 500 responses.

## Multi-organization observation

The storage model supports memberships, but the current principal/workspace selection model is optimized for a user operating within one organization context. Full multi-organization switching, invitations, and role-management workflows remain commercialization/team features rather than immediate release blockers.

## Documentation reconciliation needed

Several historical milestone files still describe earlier checkpoints or smaller test scopes. The authoritative project handoff should be preferred over stale milestone snapshots when determining current release status. In particular, historical C4 checkpoint labels, pre-promotion browser results, and old feature-progress documents must not be treated as current-tree certification.

## Audit conclusion

The V4 foundation is substantially more complete than the old blocker list implied. The appropriate next sequence is:

1. Correct the confirmed decision-signal regression.
2. Identify and remediate the confirmed frontend dependency finding with direct audit evidence.
3. Align object-store dependency failure mapping at the API boundary.
4. Reconcile authoritative project-state documentation with the post-promotion tree.
5. Execute the genuinely deployment-dependent release gates externally.
6. Move into commercial SaaS capabilities after the foundation release gates are closed.
