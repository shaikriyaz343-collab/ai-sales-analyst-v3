"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getInsights } from "../lib/api";
import { useAppState } from "../lib/app-state";
import type { InsightItem } from "../lib/types";

function tone(severity: string): string {
  return `decision-severity decision-${severity}`;
}

function score(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(0)}/100`;
}

export default function DecisionCockpit() {
  const { state } = useAppState();
  const dataset = state.dataset;
  const sessionId = state.session?.session_id;
  const [items, setItems] = useState<InsightItem[]>([]);
  const [summary, setSummary] = useState("");
  const [scopeLabel, setScopeLabel] = useState("All data");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (!dataset) {
      setItems([]);
      setLoading(false);
      return () => { active = false; };
    }
    setLoading(true);
    setError(null);
    getInsights(dataset.dataset_id, sessionId)
      .then((response) => {
        if (!active) return;
        setItems(response.insights);
        setSummary(response.summary);
        setScopeLabel(response.scope_label);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Decision signals could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [dataset?.dataset_id, sessionId]);

  if (!dataset) {
    return <div className="empty-state"><span className="empty-icon">◆</span><h1>Upload data to unlock decisions</h1><p>The decision cockpit ranks validated risks and opportunities from your business data.</p></div>;
  }

  if (loading) {
    return <div className="decision-page"><div className="skeleton-hero"/><div className="skeleton-wide"/><div className="skeleton-wide"/></div>;
  }

  if (error) {
    return <div className="panel overview-error" role="alert"><span className="eyebrow">DECISION COCKPIT UNAVAILABLE</span><h2>We couldn't load your decision feed.</h2><p>{error}</p><p>No substitute signals are shown.</p></div>;
  }

  const risks = items.filter((item) => item.kind === "risk");
  const opportunities = items.filter((item) => item.kind === "opportunity");
  const changes = items.filter((item) => item.kind === "change");

  return (
    <div className="decision-page">
      <section className="hero-row decision-hero">
        <div>
          <span className="eyebrow">DECISION COCKPIT · {scopeLabel.toUpperCase()}</span>
          <h2>What deserves your attention now?</h2>
          <p>{summary || "Validated risks and opportunities, prioritized from the same evidence engine used across the analyst."}</p>
        </div>
        <div className="confidence-card">
          <span>Trust policy</span>
          <strong>Evidence-first</strong>
          <small>{items.length ? `${items.length} validated signal${items.length === 1 ? "" : "s"}` : "No validated signals"}</small>
        </div>
      </section>

      {items.length === 0 ? (
        <section className="panel empty-signal decision-empty">
          <span className="eyebrow">NO DECISION SIGNAL</span>
          <h3>Nothing validated needs attention yet.</h3>
          <p>The analyst will not invent a warning or opportunity just to fill the feed.</p>
        </section>
      ) : (
        <>
          <section className="decision-grid decision-summary-grid">
            <article className="panel decision-count-card"><span>Priority risks</span><strong>{risks.length}</strong><small>Highest-urgency validated signals</small></article>
            <article className="panel decision-count-card"><span>Opportunities</span><strong>{opportunities.length}</strong><small>Evidence-backed upside signals</small></article>
            <article className="panel decision-count-card"><span>Changes</span><strong>{changes.length}</strong><small>Validated movement to investigate</small></article>
          </section>

          <section className="decision-feed" aria-label="Prioritized decision signals">
            {items.map((item, index) => (
              <article className="panel decision-card" key={item.id}>
                <div className="decision-rank">{String(index + 1).padStart(2, "0")}</div>
                <div className="decision-main">
                  <div className="decision-card-header">
                    <div><span className={tone(item.severity)}>{item.severity.toUpperCase()}</span><span className="decision-kind">{item.kind}</span><h3>{item.title}</h3></div>
                    <strong className="decision-value">{item.display_value}</strong>
                  </div>
                  <p className="decision-summary">{item.what_changed}</p>
                  <div className="decision-reason"><span>Why it matters</span><p>{item.why_it_matters}</p></div>
                  <div className="decision-action"><span>Recommended next step</span><p>{item.recommendation}</p></div>
                  <details className="decision-evidence">
                    <summary>Why this is ranked here</summary>
                    <div className="evidence-box">
                      <p><strong>Priority:</strong> {score(item.priority_score)}</p>
                      <p><strong>Impact:</strong> {score(item.impact_score)} · <strong>Urgency:</strong> {score(item.urgency_score)} · <strong>Evidence:</strong> {score(item.evidence_score)}</p>
                      <p><strong>Calculation:</strong> {item.evidence.calculation}</p>
                      <p><strong>Scope:</strong> {item.evidence.scope}</p>
                      <p><strong>Source fields:</strong> {item.evidence.source_fields.join(", ") || "Validated dataset"}</p>
                      {item.evidence.comparison_value !== null && item.evidence.comparison_value !== undefined && <p><strong>Comparison:</strong> {item.evidence.comparison_value}</p>}
                    </div>
                  </details>
                </div>
                <div className="decision-links"><Link href={`/dashboard/insights?signal=${encodeURIComponent(item.id)}`}>Investigate →</Link><Link href={`/dashboard/actions?signal=${encodeURIComponent(item.id)}`}>Actions →</Link></div>
              </article>
            ))}
          </section>
        </>
      )}

      <div className="overview-footer-note"><span>Ranking is deterministic and derived from validated signals; it does not create new metrics.</span><span>Priority is a ranking aid, not a claim of causal revenue impact.</span></div>
    </div>
  );
}
