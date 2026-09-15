"use client";

import { useEffect, useMemo, useState } from "react";
import { getForecast } from "../lib/api";
import type { ForecastResponse } from "../lib/types";

export default function ForecastView({ datasetId, sessionId }: { datasetId: string; sessionId?: string }) {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uplift, setUplift] = useState("10");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getForecast(datasetId, sessionId)
      .then((result) => active && setData(result))
      .catch((err) => active && setError(err instanceof Error ? err.message : "Forecast could not be loaded."))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [datasetId, sessionId]);

  const scenario = useMemo(() => {
    if (!data || !data.has_probability) return null;
    const parsed = Number(uplift);
    if (!Number.isFinite(parsed)) return null;
    const rate = Math.max(-100, Math.min(100, parsed));
    const raw = data.weighted_forecast * (1 + rate / 100);
    const value = Math.min(data.open_pipeline_value, Math.max(0, raw));
    return {
      rate,
      value,
      delta: value - data.weighted_forecast,
      capped: raw > data.open_pipeline_value,
    };
  }, [data, uplift]);

  if (loading) return <div className="forecast-page"><div className="skeleton-hero"/><div className="skeleton-wide"/></div>;

  if (error) {
    return <div className="panel overview-error" role="alert">
      <span className="eyebrow">FORECAST UNAVAILABLE</span>
      <h2>We couldn't build a validated forecast.</h2>
      <p>{error}</p>
      <p>No substitute figures are shown.</p>
    </div>;
  }

  if (!data) return null;

  return <div className="forecast-page">
    <section className="hero-row">
      <div>
        <span className="eyebrow">{data.business_model_label ?? "SALES FORECAST"} · {data.scope_label.toUpperCase()}</span>
        <h2>What is likely to close?</h2>
        <p>{data.basis_note}</p>
      </div>
      <div className="confidence-card">
        <span>Forecast basis</span>
        <strong>{data.has_probability ? "Probability-weighted" : "Open pipeline"}</strong>
        <small>{data.open_opportunities.toLocaleString()} open opportunities</small>
      </div>
    </section>

    <section className="metric-grid">
      <ForecastMetric label="Weighted forecast" value={formatAmount(data.weighted_forecast)} detail="Expected value from open opportunities" />
      <ForecastMetric label="Open pipeline" value={formatAmount(data.open_pipeline_value)} detail="Total value still open" />
      <ForecastMetric label="Open opportunities" value={data.open_opportunities.toLocaleString()} detail={data.has_probability ? "Probability field validated" : "No validated probability field"} />
    </section>

    {data.has_probability && scenario && <section className="panel forecast-scenario">
      <div className="section-heading">
        <div><span className="eyebrow">SCENARIO ANALYSIS</span><h3>What if the forecast improves?</h3></div>
        <span className="section-kicker">Illustrative only</span>
      </div>
      <p>Model a relative change to the current weighted forecast. This does not alter the uploaded data or claim that the probability will change.</p>
      <div className="scenario-controls">
        <label htmlFor="forecast-uplift">Scenario improvement (%)</label>
        <input id="forecast-uplift" type="number" min="-100" max="100" step="1" value={uplift} onChange={(event) => setUplift(event.target.value)} />
      </div>
      <div className="metric-grid">
        <ForecastMetric label="Scenario forecast" value={formatAmount(scenario.value)} detail={`${scenario.rate}% relative change assumption`} />
        <ForecastMetric label="Change vs baseline" value={formatAmount(scenario.delta)} detail={scenario.capped ? "Capped at open pipeline" : "Illustrative delta"} />
      </div>
      <div className="forecast-evidence-grid">
        <div><span>Assumption</span><strong>Baseline weighted forecast × (1 + improvement ÷ 100)</strong></div>
        <div><span>Boundary</span><strong>Scenario cannot exceed the validated open pipeline.</strong></div>
        <div><span>Truth policy</span><strong>Scenario values are modeled, not observed.</strong></div>
      </div>
    </section>}

    {!data.has_probability && <section className="panel forecast-scenario">
      <div className="section-heading">
        <div><span className="eyebrow">SCENARIO ANALYSIS</span><h3>Scenario modeling is not available yet</h3></div>
        <span className="section-kicker">Data-dependent</span>
      </div>
      <p>The uploaded dataset has no validated probability field, so we will not invent a probability adjustment.</p>
    </section>}

    <section className="panel forecast-basis">
      <div className="section-heading">
        <div><span className="eyebrow">WHY THIS NUMBER</span><h3>Trace the forecast back to the data</h3></div>
        <span className="section-kicker">Evidence-backed</span>
      </div>
      <div className="forecast-evidence-grid">
        <div><span>Calculation</span><strong>{data.evidence.calculation}</strong></div>
        <div><span>Source fields</span><strong>{data.evidence.source_fields.join(", ") || "Validated dataset"}</strong></div>
        <div><span>Source records</span><strong>{data.evidence.source_records.join(", ") || "No stable record identifiers available"}</strong></div>
        <div><span>Scope</span><strong>{data.evidence.scope}</strong></div>
      </div>
    </section>

    <section className="panel forecast-monthly">
      <div className="section-heading">
        <div><span className="eyebrow">MONTHLY OUTLOOK</span><h3>Expected value by close month</h3></div>
        <span className="section-kicker">Deterministic</span>
      </div>
      {data.monthly_forecast.length ? <div className="forecast-table">
        <div className="forecast-table-row forecast-table-head"><span>Month</span><span>Expected value</span><span>Weighted forecast</span><span>Open opportunities</span></div>
        {data.monthly_forecast.map((item) => <div className="forecast-table-row" key={item.month}>
          <strong>{item.month}</strong>
          <span>{formatAmount(item.expected_value)}</span>
          <span>{formatAmount(item.weighted_forecast)}</span>
          <span>{item.opportunities.toLocaleString()}</span>
          {item.evidence.source_records.length > 0 && <details className="forecast-row-evidence"><summary>Records</summary><span>{item.evidence.source_records.join(", ")}</span></details>}
        </div>)}
      </div> : <div className="empty-signal">No dated open opportunities are available for a monthly outlook.</div>}
    </section>

    <section className="overview-footer-note">
      <span>Forecast is calculated from the current dataset and analytical scope.</span>
      <span>{data.has_probability ? "Probability-weighting is supported by validated data." : "Probability data is unavailable; no weighted estimate is presented."}</span>
    </section>
  </div>;
}

function ForecastMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <article className="metric-card">
    <span>{label}</span>
    <strong>{value}</strong>
    <small>{detail}</small>
  </article>;
}

function formatAmount(value: number) {
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);
}
