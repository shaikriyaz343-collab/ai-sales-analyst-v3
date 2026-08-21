# v3.4 Hardening

P0 fixes:
- Review navigation reduced to one source of truth.
- Applying a scope now rebuilds data quality, adaptive modules, business packs,
  business brief, and dashboard-visible metrics from the scoped dataframe.
- Full-file report remains intact for default Q&A.
- Q&A uses scoped business packs only when the user explicitly enables
  "Use the current dashboard scope for this question".
- Partial date ranges cannot be applied.
- Full-source date range does not count as an active filter.
- Concentration findings are suppressed for a dimension explicitly filtered
  to one entity.

P1 fixes:
- Business-specific scope dimensions for retail, pipeline, subscription, and
  services.
- Scope banner includes applied dimensions.
- Business-specific Q&A remains deterministic.
- PDF revenue is labeled "Recorded Revenue" and explains the distinction from
  net realized sales when return data exists.
- Expanded regression coverage for scope and Q&A.

Validation:
- 48 unit/integration tests passed.
- Runtime diagnostics passed.
- Release-contract diagnostics passed.
- Scope metric regression matrix passed.
- Retail PDF generation passed.
