# AI Business Analyst v3 — Production Acceptance Gate

## Release principle

This build is treated as a release candidate only when the functional test suite,
runtime diagnostics, and release-contract diagnostics all pass.

## Acceptance matrix

### 1. Ingestion
- CSV upload
- Excel/XLSX/XLS dependencies
- schema profiling
- data quality
- business-type detection
- additional/unmapped fields

### 2. Four representative business archetypes
- Transactional / Retail Sales
- Sales Pipeline
- Subscription / Recurring Revenue
- Services / Professional Services

### 3. Review Your Business
Each business model is exercised through its business-specific modules plus:
- Overview / Business Brief
- What Needs Your Attention
- Performance
- Ask Your Business Analyst
- Executive Report
- Data Quality

### 4. State and navigation
- No widget default/session-state conflict
- No post-render widget mutation
- Programmatic navigation uses callbacks/pending navigation
- Long Retail navigation uses compact primary + overflow sections
- New-file reset returns to Overview
- Investigate-this navigation is safe

### 5. Filters / scope
- Date-only filter
- Product-only filter
- Customer-only filter
- Combined filters
- Zero-row combinations
- Pre-Apply match count
- Revenue preview when available
- Apply disabled for zero-row scope
- Show full business reset
- Scoped dashboard is explicit
- Q&A defaults to full file unless scoped-view is explicitly selected

### 6. Factual Q&A
- Product revenue ranking
- Unit ranking
- Customer ranking
- Month-aware questions
- Unsupported/vague questions do not receive guessed KPIs
- Business-specific Q&A for pipeline, subscription, services
- Nullable response schema uses supported anyOf JSON Schema

### 7. Analyst intelligence
Findings use:
- What happened
- Why it matters
- Recommended action
- Investigate next
- Explicit entity names
- No meaningless Investigate button on the no-risk fallback state

### 8. Executive reporting
- Metrics agree with the report context
- Business-specific recommendations
- Executive PDF generation for all four representative files

### 9. Production hygiene
- No deprecated use_container_width calls
- No known widget-state anti-patterns
- Required modules present
- No invalid Q&A schema unions
- No known date arithmetic deprecation in scope handling

## Verification executed before packaging

- Python syntax audit: PASS
- Unit/integration suite: 44 tests PASS
- Runtime diagnostics (live-path simulation): 35 PASS
- Release-contract diagnostics: 7 PASS
- Total runtime/release checks: 42 PASS
- Four representative datasets exercised
- Executive PDF generated for all four representative datasets

## External implementation guidance used

The state/navigation design follows Streamlit's documented widget lifecycle: widget
state should be initialized before widget creation, and widget state should not be
mutated through Session State after the widget has been instantiated.

Structured Q&A schemas use JSON Schema `anyOf` for nullable fields, matching the
current Google Gen AI SDK guidance.

Comparable product patterns considered during hardening:
- governed/grounded analytical answers
- filterable dashboards
- guided insights and follow-up investigation
- business-owner-oriented executive summaries
