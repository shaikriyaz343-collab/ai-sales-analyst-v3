# AI Business Analyst v3 — Product Notes

## The product thesis

The app is not intended to be another generic dashboard. Its primary job is to answer four business questions:

1. What did I actually upload and what can it tell me?
2. What changed or deserves attention?
3. What should I investigate next?
4. Can I trust the answer and reproduce the calculation?

## Evidence-first experience

Every important finding is designed to connect:

**Observed fact → business implication → recommended action → investigation question → verified calculation basis**

That is the core product pattern used throughout the Business Brief, Attention view, Q&A, and Executive Report.

## What was deliberately removed or constrained

- Generic AI answers for ambiguous factual questions.
- Generic “selected reporting period” wording when the actual data period is known.
- Forecast calculations that include already-closed opportunities.
- Subscription MRR totals that blindly sum multiple dated snapshots.
- Customer/client concentration calculations based only on a truncated top-10 table.
- Causal language when the source file does not contain causal evidence.
- Stale Q&A answers remaining visible after the question is edited.

## Unique product layer

The differentiator is the capability map: the app describes what the uploaded file supports and builds the business brief from those capabilities. A retail file with product/customer/discount/return data gets different analysis from a services file with hours/client/employee data without requiring the user to choose a report template first.
