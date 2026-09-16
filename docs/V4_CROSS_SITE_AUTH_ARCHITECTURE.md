# V4 Production Cross-Site Authentication Architecture

Date: 2026-09-16

## Problem

The current deployment uses separately addressable Railway frontend and API services. That makes the authentication cookie cross-site when the services use different registrable domains. Modern browser privacy controls can block such cookies even when the server correctly sets `Secure` and `SameSite=None`.

This is a deployment architecture concern, not a reason to weaken tenant authorization or disable credentialed requests.

## Required production contract

### Preferred topology: same-site application and API

Expose the frontend and API under the same registrable domain, for example:

```text
https://app.<customer-domain>/
https://api.<customer-domain>/
```

or route the API through the frontend origin:

```text
https://app.<customer-domain>/api/*
```

The hosting layer may use separate services internally, but the browser should see a same-site application/API relationship. This minimizes third-party-cookie policy friction while preserving the existing HTTP-only secure session cookie model.

### Split-host fallback

When the frontend and API must remain on different registrable domains, production must explicitly use:

- `V4_AUTH_SECURE_COOKIE=true`
- `V4_AUTH_COOKIE_SAMESITE=none`
- a production `__Host-` cookie name
- an exact HTTPS `V4_FRONTEND_ORIGINS` allowlist
- credentialed browser requests

This configuration is secure against several common cookie misconfigurations, but it does not guarantee compatibility when the browser blocks third-party cookies. A browser-policy exception should therefore not be treated as the desired long-term SaaS architecture.

## Non-negotiables

Do not solve cross-site friction by:

- making the auth cookie non-secure;
- using a broad wildcard CORS origin with credentials;
- storing the session token in localStorage or other script-readable storage;
- weakening organization/workspace/dataset authorization checks;
- disabling security headers or trusted-host validation.

## Current implementation alignment

The backend already enforces:

- production `__Host-` cookie naming;
- `Secure` cookies in production;
- `SameSite=None` only when secure cookies are enabled;
- HTTPS-only production frontend origins;
- credentialed CORS restricted to the configured origin list;
- trusted-host validation;
- centralized authenticated tenant/workspace access checks.

Regression coverage is maintained in `tests_v4_saas/test_security_contract.py` for the secure-cookie and CORS contract.

## Release gate

Issue #13 should remain open until the deployment owner selects and records the production topology and verifies it in a real browser environment. The repository does not invent a provider-specific custom-domain mapping; it defines the security contract the chosen deployment must satisfy.
