# V4 Paddle External Activation Checklist

Date: 2026-09-19

This checklist is intentionally external/provider-facing. Repository code cannot complete or certify these steps.

## Sandbox

- [ ] Create/approve the Paddle sandbox vendor account.
- [ ] Create the V4 software product/catalog entries.
- [ ] Create Starter recurring monthly price: USD 49.
- [ ] Create Growth recurring monthly price: USD 149.
- [ ] Record sandbox Starter/Growth price IDs.
- [ ] Configure and approve the default payment link required for Paddle Checkout.
- [ ] Create sandbox API key.
- [ ] Create the webhook/notification destination secret.
- [ ] Configure the notification destination as:
  `https://ai-sales-analyst-v3-production.up.railway.app/api/v1/commercial/webhook`
- [ ] Enable the subscription lifecycle notifications documented in the integration runbook.
- [ ] Put sandbox credentials/price IDs into Railway without committing them.

## Application verification

- [ ] Confirm `V4_BILLING_PROVIDER=paddle`.
- [ ] Confirm `V4_PADDLE_ENVIRONMENT=sandbox`.
- [ ] Confirm the hosted checkout endpoint returns a Paddle checkout URL for Starter and Growth.
- [ ] Perform one real sandbox checkout.
- [ ] Capture the Paddle transaction/subscription identifiers.
- [ ] Confirm the signed webhook is accepted by production.
- [ ] Confirm the organization changes from trial to the provider-reported subscription state.
- [ ] Confirm entitlements and usage limits reflect the paid plan.
- [ ] Confirm a duplicate webhook is ignored.
- [ ] Confirm an older/out-of-order webhook cannot roll back newer subscription state.
- [ ] Confirm the customer portal session opens and is scoped to the linked subscription.
- [ ] Confirm the daily reconciliation endpoint can read/repair the same subscription.

## Live activation

Do not switch production billing on until the sandbox evidence is preserved and reviewed.

- [ ] Complete/approve the live Paddle seller account.
- [ ] Create live V4 products and recurring monthly prices.
- [ ] Record live Starter/Growth price IDs separately from sandbox IDs.
- [ ] Create the live API key.
- [ ] Create/configure the live notification destination secret.
- [ ] Set `V4_PADDLE_ENVIRONMENT=live` only after the live catalog and webhook path are verified.
- [ ] Run an approved live lifecycle test.
- [ ] Preserve the exact transaction/subscription/webhook evidence with release SHA and Railway deployment identity.
- [ ] Enable live paid access only after the final human review.

## Evidence rule

A repository test proves application behavior. A Paddle dashboard/transaction/webhook artifact proves provider execution. Keep both and tie them to the same release candidate before closing the commercial launch gate.
