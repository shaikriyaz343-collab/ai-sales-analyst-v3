# AI Business Analyst v3 — Product & Trust Audit

## Product direction

This release shifts the product from a collection of business-type tabs toward a capability-first analyst experience:

Uploaded file → semantic mapping → capability map → evidence-first Business Brief → ranked signals → investigation/Q&A → executive report.

## Changes in this release

### Trust and data sufficiency
- Schema match is separate from data coverage.
- Small datasets are explicitly marked directional.
- Data-quality is always accessible in the navigation.
- Analysis basis and limitations are shown in the Business Brief.
- Missing cost, history, return-amount, or causal fields are stated rather than inferred.

### Business Brief
- Overview is business-model-aware and uses the same verified metrics as the rest of the app.
- The Brief surfaces the most material signals first instead of making users read every table.
- Each signal is framed as what happened, why it matters, recommended action, and a follow-up investigation.
- The Brief also exposes which dimensions and metrics the file supports.

### Q&A integrity
- The application now uses `sales_query_engine_v1` as the canonical factual query engine.
- Obvious entity/metric intent is guarded deterministically before AI output is trusted.
- The app no longer displays an old answer for an edited question.
- A Clear action resets the Q&A state.
- Answers expose their scope, calculation, source fields, and limitations.
- Transactional questions use the full uploaded dataset by default.
- Users can explicitly opt into the current filtered dashboard scope.
- Non-transactional questions use verified business-pack calculations; unsupported causal conclusions are declined instead of guessed.

### Pipeline semantics
- Total opportunity value, open pipeline value, won value, and lost value are separated.
- Forecast uses open opportunities only.
- Probability-weighted forecast is calculated from expected-close date and probability when available.
- Win rate is labeled as value-based.

### Subscription semantics
- When repeated dated snapshots exist, MRR is calculated from the latest snapshot rather than summing multiple periods.
- Customer-level churn is used when customer and churn status are available.
- Record-level churn is clearly distinguished when customer-level calculation is not possible.

### Professional services semantics
- Billings, hours, revenue/hour, client contribution, and employee hours are kept distinct.
- Client concentration uses the actual billings/revenue field detected in the file.
- Utilization is not presented as employee quality or productivity without the required context.

### Scope / filtering
- Dashboard filters are now explicit and separated from Q&A scope.
- The default dashboard is the full business view.
- Date/product/customer filters create an exploratory view.
- Q&A uses the full file unless the user explicitly chooses the scoped view.

### Executive report
- The PDF includes data coverage, executive takeaways, why the findings matter, and recommended actions in addition to KPI/module tables.

## Design references studied

- Power BI Copilot: understand data → dig deeper → write a summary, with reference footnotes and a “how arrived at this” exploration path.
- Tableau Pulse: drivers, trends, contributors, outliers, guided questions, metric context, and filtered exploration.
- Tableau Data Guide / Explain Data: dashboard context, applied filters, outliers, and mark-level explanations.
- Salesforce CRM Analytics: selection-based filters, interactive dashboards, and drill-down exploration.
- Looker Conversational Analytics: natural-language questions grounded in a governed semantic model.
- Metabase: dashboards composed of reusable analytical questions, shared filters, and natural-language query workflows.

## Product differentiation

The intended differentiator is not another generic dashboard or generic chatbot. The product is an evidence-first business brief that adapts to the actual capabilities in a user's file and links every important finding to a verified calculation and a next investigation.

## Validation completed

- 28 regression tests passing.
- Four representative business archetypes exercised: retail, sales pipeline, subscription, and professional services.
- Application top-level import validated with Streamlit runtime stubs.
- Adaptive PDF generated successfully for all four representative datasets.
- Q&A intent guardrails tested for product ranking, unit ranking, customer ranking, month-specific ranking, missing periods, and unsupported/vague questions.

## Known runtime limitation

The execution environment used for code validation did not provide a working Streamlit browser runtime, so browser-level interaction was not simulated here. The attached walkthroughs remain the browser-level evidence source for UI behavior, and the package should receive one final real-browser walkthrough before production deployment.
