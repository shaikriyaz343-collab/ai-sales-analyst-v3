# AI Sales Analyst V4 — Security Review

Date: 2026-09-16
Branch reviewed: `v4/saas-foundation`
Application behavior checkpoint: `371aa5caf00308b98faeba58bf4c5736bb995b39`

## Scope

This repository-side review covers the security controls present in the promoted V4 application tree. It is separate from deployment-provider evidence and does not claim independent certification of production infrastructure.

## Authentication and session controls

- Authentication is required for protected API routes through the central `require_user` dependency.
- Sessions use opaque random tokens; the database stores a SHA-256 token hash rather than the raw session token.
- Sessions have idle and absolute expiry controls and support explicit revocation and revoke-all behavior.
- Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a per-password random salt.
- Authentication and signup flows have IP- and email-scoped rate limits.
- Security events store hashed email/IP identifiers rather than raw identifiers and do not store passwords or session tokens.

## Tenant/workspace authorization

- Dataset access is checked against the authenticated organization and workspace membership.
- Analysis session access is checked against the authenticated organization and workspace membership.
- Session/dataset consistency is validated before scoped operations proceed.
- Existing regression coverage includes a cross-organization dataset access denial test.

## Object-store and persistence boundaries

- Production requires external persistence and rejects local persistence mode.
- Production PostgreSQL configuration requires an explicit TLS `sslmode`.
- Custom production object-store endpoints require HTTPS.
- Partial object-store credentials are rejected.
- Production object-store prefixes must be non-empty and cannot contain parent-directory segments.
- Persistence dependency/configuration failures are mapped to HTTP 503 at the API boundary rather than leaking as generic application errors.

## Browser and HTTP security

- Production authentication cookies require the `__Host-` prefix and `Secure`.
- `SameSite=None` is accepted only when the secure-cookie contract is enabled.
- CORS is credentialed but restricted to the configured frontend-origin allowlist.
- Production trusted hosts cannot contain loopback hosts.
- Production frontend origins must use HTTPS.
- Security headers include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and production HSTS.

## Error handling and logging

- Central error handling returns sanitized client-facing error messages for unexpected failures.
- Database and object-store dependency failures produce 503 responses.
- Runtime logs redact configured database/object-store secret values when present.
- Correlation/request identifiers are propagated through telemetry without exposing credentials.

## Regression coverage added in this review

`tests_v4_saas/test_security_contract.py` explicitly verifies:

- production `SameSite=None` requires secure cookies;
- security response headers are present when enabled;
- the declared frontend origin receives credentialed CORS headers;
- an undeclared origin is not echoed by CORS.

## Findings

No new application-level security blocker was identified in this repository review beyond the already-tracked production cross-site domain/cookie architecture issue (#13). The split Railway frontend/API topology may require browser privacy-policy exceptions for third-party cookies; this is a deployment architecture constraint rather than a failure of the repository's secure-cookie configuration.

Deployment-dependent evidence remains outside this review: exact deployed Playwright acceptance, Linux/container capacity measurements, controlled dependency-failure rehearsal, deployed restart/recovery, deployed tenant-isolation evidence, and measured production monitoring evidence.

## Conclusion

The promoted application tree has explicit controls for authentication, session lifecycle, tenant/workspace authorization, persistence boundaries, CORS/trusted hosts, security headers, rate limiting, secret redaction, and dependency-error handling. This document records the repository-side security review and its residual deployment-dependent gates; it does not certify the production environment itself.
