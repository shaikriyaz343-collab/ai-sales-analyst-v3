# V4 Payment Provider Decision Record — 2026-09-18

Status: provider not selected. This document records current public provider facts and the integration boundary; it does not authorize an account or a production payment integration.

## Decision criteria

The provider decision should consider:

- whether the legal business entity can open the account now
- settlement country/currency requirements
- subscription billing support
- webhook reliability and signature verification
- refund/cancellation/customer-portal support
- tax/VAT handling responsibility
- transaction economics at our expected ticket size
- operational burden for a one-founder + AI operating model
- customer payment-method coverage in the initial GCC/India markets

## Current public facts

### Stripe

Stripe lists the United Arab Emirates among supported countries. Stripe states that new India accounts are invite-only, and Indian businesses accepting international payments need an active approved Stripe account and the required export-related setup; Stripe says India accounts can accept international payments in more than 135 currencies. See:

- https://stripe.com/global
- https://support.stripe.com/questions/stripe-accounts-are-invite-only-in-india
- https://support.stripe.com/questions/accepting-international-payments-from-stripe-accounts-in-india

### Paddle

Paddle states that it supports software businesses in more than 200 countries and territories, including the United Arab Emirates, and operates as a Merchant of Record. Its current public pricing page lists 5% + $0.50 per Checkout transaction and says the package includes payment handling, tax compliance, fraud/chargeback protection and billing support.

- https://developer.paddle.com/concepts/sell/supported-countries-locales/
- https://www.paddle.com/pricing

### Lemon Squeezy

Lemon Squeezy lists India and the United Arab Emirates among countries supported for bank payouts. It supports AED as a selling currency. Its public pricing is 5% + $0.50 per transaction, with additional fees possible; its documentation says subscription payments can carry an additional fee and it acts as Merchant of Record for sales-tax/VAT handling.

- https://docs.lemonsqueezy.com/help/getting-started/supported-countries
- https://docs.lemonsqueezy.com/help/payments/currencies
- https://www.lemonsqueezy.com/pricing
- https://docs.lemonsqueezy.com/help/getting-started/fees
- https://docs.lemonsqueezy.com/help/payments/merchant-of-record

### Telr

Telr documents recurring-payment and subscription capabilities and markets recurring payments specifically for UAE businesses. Its current documentation describes both invoice-based subscriptions and recurring card transactions.

- https://docs.telr.com/reference/subscriptions-recurring-payments
- https://docs.telr.com/reference/recurring-transactions-1
- https://get.telr.com/

## Architecture decision

The application should remain provider-neutral.

The code now defines a provider contract with:

- checkout-session creation
- signed webhook verification
- provider event identity for idempotency
- customer portal URL generation

No provider credentials, API calls, checkout sessions, webhook handlers, or production billing mutations are implemented by the commercial foundation.

## Next decision

First confirm the legal entity/country that will receive settlement. Then choose the provider using the criteria above. After that choice, implement one adapter plus sandbox tests, webhook idempotency, subscription-state reconciliation, and billing browser acceptance before enabling production checkout.

This decision record intentionally does not select a provider on behalf of the operator.
