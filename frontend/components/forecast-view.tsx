"use client";

import { useEffect, useState } from "react";
import { getForecast } from "../lib/api";
import type { ForecastResponse } from "../lib/types";

export default function ForecastView({ datasetId, sessionId }: { datasetId: string; sessionId?: string }) {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      <ForecastMetric label="Weighted forecast" value={formatMoney(data.weighted_forecast)} detail="Expected value from open opportunities" />
      <ForecastMetric label="Open pipeline" value={formatMoney(data.open_pipeline_value)} detail="Total value still open" />
      <ForecastMetric label="Open opportunities" value={data.open_opportunities.toLocaleString()} detail={data.has_probability ? "Probability field validated" : "No validated probability field"} />
    </section>

    <section className="panel forecast-basis">
      <div className="section-heading">
        <div><span className="eyebrow">WHY THIS NUMBER</span><h3>Trace the forecast back to the data</h3></div>
        <span className="section-kicker">Evidence-backed</span>
      </div>
      <div className="forecast-evidence-grid">
        <div><span>Calculation</span><strong>{data.evidence.calculation}</strong></div>
        <div><span>Source fields</span><strong>{data.evidence.source_fields.join(", ") || "Validated dataset"}</strong></div>
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
          <span>{formatMoney(item.expected_value)}</span>
          <span>{formatMoney(item.weighted_forecast)}</span>
          <span>{item.opportunities.toLocaleString()}</span>
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

function formatMoney(value: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}
