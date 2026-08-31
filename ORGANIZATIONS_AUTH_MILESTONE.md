# V4 Organizations + Authentication Milestone

Baseline: `7fa0348` — Build V4 Saved Intelligence.

This milestone introduces a tenant-first SaaS identity foundation without changing the existing deterministic analytics engines.

## Included

- Organization, membership, and workspace persistence in SQLite.
- Email/password authentication using PBKDF2 password hashes and opaque, server-side session tokens.
- HttpOnly, SameSite authentication cookie with configurable secure-cookie behavior.
- Authenticated `/auth/me` contract and sign-out lifecycle.
- Owner/admin workspace creation and organization-scoped workspace listing.
- Dataset ownership metadata (`organization_id`, `workspace_id`).
- Analysis session ownership metadata and workspace-aware authorization.
- Authentication-aware frontend state and protected dashboard routing.
- Workspace selector and workspace creation controls.
- Authenticated API client with credentialed requests.
- Playwright global authentication setup with deterministic browser storage state.
- Independent unauthenticated auth lifecycle coverage.
- Tenant-isolation API coverage.

## Invariants

Every customer-owned analytical object is reachable through:

`user → organization → workspace → dataset → analysis session → scope → intelligence`

The analytical calculation engines remain unchanged; authorization is enforced at the API boundary before a dataset/session can be analyzed.

## Deferred by design

- Password reset / email verification.
- SSO/SAML/OIDC.
- Organization member invitations and role management UI.
- External database migration/managed Postgres.
- Usage metering, plan entitlements, billing, and production secret management.

Those belong to the following SaaS milestones and should be built on this identity boundary rather than retrofitted later.
