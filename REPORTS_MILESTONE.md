# V4 Reports Milestone

## Product intent
Reports turns the validated session into a decision-ready executive brief.

## Source of truth
Reports reuses the existing Overview, Insights, and Actions services for the current dataset and analytical scope. It does not recalculate business metrics in a separate reporting engine.

## Current capabilities
- Executive summary
- KPI cards
- What changed
- What needs attention
- Opportunities
- Recommended actions
- Evidence and scope
- Print / Save PDF browser workflow
- Dataset replacement consistency

## Validation
- Report service tests cover all four supported business models.
- Scoped-report test verifies evidence and scope propagation.
- V4 Playwright acceptance covers report rendering and dataset replacement.

## Next product work
Reports will later gain persistent saved reports, scheduled delivery, sharing, and server-side PDF generation once the SaaS persistence/notification layer is introduced.
