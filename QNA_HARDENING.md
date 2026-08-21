# Q&A Hardening

The Ask Your Business Analyst experience was tightened after review of the
latest screen recording.

## User experience
- Added a visible Clear button.
- Old answers are not shown when the user edits the question.
- Answered-question state is tracked separately from the input text.
- New questions require a fresh calculation before an answer is displayed.

## Accuracy guardrails
- Explicit product/customer wording overrides ambiguous AI entity selection.
- "Best/top/most" + product/customer is forced into a deterministic ranking query.
- Revenue/unit/order/AOV wording is mapped to the corresponding verified metric.
- Named months in the user's question take precedence over ambiguous planner output.
- Unsupported vague questions no longer receive a guessed KPI answer.
- Full-period answers explicitly state the uploaded data period.
- Missing-month queries explicitly state which periods are available.

## Business-specific Q&A
Verified deterministic Q&A is available for:
- Transactional / retail sales
- Sales pipeline
- Subscription / recurring revenue
- Professional services

The application prefers verified calculations over free-form AI answers for factual
questions. The investigation agent remains available for "why/change" analysis.
