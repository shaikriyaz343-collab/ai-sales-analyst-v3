# AI Business Analyst v2 — Consolidated Release

This package consolidates the fixes and product improvements identified across
the recorded UI walkthroughs.

## Trust and UX
- Schema match is separated from data coverage.
- Small datasets are explicitly marked as limited/directional.
- The profile explains how many recognizable business dimensions and analysis
  areas the uploaded file supports.
- "Analyze my business" is the action after data understanding.
- Existing selected Review Your Business section persists through Streamlit
  reruns.
- New file selection resets stale analysis and returns to Overview.

## Adaptive business experience
- Overview is business-type aware for retail, pipeline, subscription, and
  professional services.
- Available analysis is driven by the capabilities detected in the file.
- Business-specific modules remain adaptive rather than forcing a retail report.

## Analyst Intelligence
- Material findings include what happened, why it matters, recommended action,
  investigate next, and a follow-up question.
- Findings can open Ask Your Business Analyst with a relevant question.
- Executive Report uses real findings and recommended actions rather than
  generic instructions.

## Pipeline forecast
- Forecast is shown only when expected-close date and amount are available.
- Probability-weighted forecast is calculated when probability is present.
- Missing forecast inputs are explained rather than presented as an error.

## Validation
- Existing regression suite plus consolidated product tests.
- Four representative archetypes exercised: retail, sales pipeline,
  subscription, and professional services.
