# V4 Monitoring / Alerts milestone

Monitoring is a deterministic rule layer over the existing analytical session.

A monitor is defined by:
- validated Overview metric
- comparison operator
- numeric threshold
- cadence metadata (manual, daily, weekly)
- current session scope

Evaluation reuses `build_overview()` so values and evidence remain consistent with Overview, Insights, Actions, and Reports.

Dataset replacement clears monitoring rules and events for the session so prior alerts cannot leak into the new dataset.

The current milestone provides manual evaluation. A background scheduler/delivery layer is intentionally deferred to the SaaS infrastructure phase.
