# v3.1 — Scope & Q&A Hardening

## Observed issues

1. The "Explore a subset of the business" panel was materially useful only for
   retail because the UI was hard-coded around `product` and `customer`.
   Subscription/pipeline/services either showed only a date control or no
   meaningful business dimensions.

2. Q&A could answer a question about a customer using a product-revenue ranking.
   The observed example was:
   "Which customer bought the most products?"
   The correct intent is customer + quantity ranking.

3. Vague questions such as "Which product performed well?" were being mapped
   toward a metric without the user defining what "performed well" means.

## v3.1 behavior

### Adaptive scope
The scope panel now derives filters from the detected business model:

- Retail: Product, Customer
- Sales Pipeline: Salesperson, Pipeline stage
- Subscription: Customer, Plan
- Services: Client, Service

A date filter is included whenever a usable date exists. The panel explicitly
states which dimensions were found and that the scope changes the dashboard view,
not the uploaded source data.

### Q&A
The query planner now applies deterministic subject/metric guardrails before
accepting an ambiguous LLM interpretation.

Examples:

- "Which customer bought the most products?" → Customer + Units Sold
- "Which product made the most revenue in August?" → Product + Revenue + August
- "Which product performed well?" → clarification instead of an invented KPI

## Verification

- 44 unit/integration tests: PASS
- 35 live runtime diagnostics: PASS
- 7 release-contract diagnostics: PASS
- 42 runtime/release checks: PASS
- Four representative business files exercised
