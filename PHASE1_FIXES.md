# AI Business Analyst v2 — Phase 1 Fixes

## Correctness
- Forecast is advertised only when expected-close date and amount fields are available.
- Pipeline forecast now calculates expected pipeline, probability-weighted forecast, and monthly expected-close values.
- Forecast clearly explains when required fields are missing.
- User-facing terminology is "Ask Your Business Analyst".

## Business-specific insight
- What Needs Your Attention now adds business-model-specific signals for:
  - sales pipeline
  - subscription
  - professional services
- Neutral datasets no longer show a vague "nothing unusual" message without guidance.

## Executive report
- Executive Report now previews the main KPIs before PDF generation.
- It shows business-specific key metrics and next-step guidance.

## Validation
- Retail, pipeline, subscription, and services upload/analyze/UI paths passed.
- Regression suite: 11 tests, all passing.
