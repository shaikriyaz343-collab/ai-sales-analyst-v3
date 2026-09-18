"use client";

import { useEffect, useMemo, useState } from "react";
import { createCommercialCheckout, getCommercialEntitlements, getCommercialPortal } from "../../../lib/api";
import type { CommercialEntitlements, CommercialPlan } from "../../../lib/types";

const USAGE_LABELS: Record<string, string> = {
  dataset_uploads: "Dataset uploads",
  analyst_questions: "Analyst questions",
  reports: "Reports",
  monitoring_rules: "Monitoring rules",
  saved_intelligence: "Saved intelligence",
};

function reasonLabel(reason: string): string {
  return reason.replaceAll("_", " ");
}

function usageLabel(key: string): string {
  return USAGE_LABELS[key] ?? key.replaceAll("_", " ");
}

function planPrice(plan: CommercialPlan): string {
  return plan.price_usd_monthly === 0 ? "Free" : `$${plan.price_usd_monthly}/month`;
}

export default function BillingPage() {
  const [data, setData] = useState<CommercialEntitlements | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyPlan, setBusyPlan] = useState<string | null>(null);


  async function startCheckout(planId: string) {
    setBusyPlan(planId);
    setError(null);
    try {
      const session = await createCommercialCheckout(planId);
      window.location.assign(session.checkout_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout could not be started.");
    } finally {
      setBusyPlan(null);
    }
  }

  async function openPortal() {
    setError(null);
    try {
      const result = await getCommercialPortal();
      window.location.assign(result.portal_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Customer portal could not be opened.");
    }
  }

  useEffect(() => {
    let active = true;
    getCommercialEntitlements()
      .then((response) => {
        if (!active) return;
        setData(response);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Billing information could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const currentPlan = useMemo(
    () => data?.catalog.find((plan) => plan.plan_id === data.subscription.plan_id),
    [data],
  );

  if (loading) {
    return (
      <div className="billing-page">
        <section className="hero-row"><div><span className="eyebrow">BILLING</span><h1>Plan & usage</h1><p>Loading your commercial account state.</p></div></section>
        <div className="billing-skeleton" />
        <div className="billing-plan-grid">{[1, 2, 3].map((item) => <div className="panel billing-card billing-skeleton-card" key={item} />)}</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="billing-page">
        <section className="panel overview-error" role="alert">
          <span className="eyebrow">BILLING UNAVAILABLE</span>
          <h2>We couldn't load your plan state.</h2>
          <p>{error ?? "No commercial account state was returned."}</p>
          <p>No substitute billing data is shown.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="billing-page">
      <section className="hero-row billing-hero">
        <div>
          <span className="eyebrow">BILLING · ORGANIZATION</span>
          <h1>Plan & usage</h1>
          <p>See the organization's current access and usage. Paid checkout is enabled when the configured billing provider is ready.</p>
        </div>
        <div className="confidence-card">
          <span>Current access</span>
          <strong>{data.subscription.plan_name ?? "No paid plan"}</strong>
          <small>{reasonLabel(data.subscription.access_reason)}</small>
        </div>
      </section>

      <section className="panel billing-status-panel">
        <div>
          <span className="eyebrow">CURRENT PLAN</span>
          <h2>{data.subscription.plan_name ?? "Access inactive"}</h2>
          <p>{data.subscription.access_active ? "Your organization currently has access to the product." : "Your organization does not currently have active product access."}</p>
        </div>
        <div className="billing-limits">
          <div><span>Seats</span><strong>{data.entitlements.max_seats}</strong></div>
          <div><span>Workspaces</span><strong>{data.entitlements.max_workspaces}</strong></div>
          <div><span>Usage period</span><strong>{data.usage_period_start ? new Date(data.usage_period_start).toLocaleDateString() : "—"}</strong></div>
          {data.billing.customer_portal_available && (
            <button type="button" className="secondary-button" onClick={openPortal}>Manage billing</button>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><span className="eyebrow">USAGE</span><h2>Current period</h2></div></div>
        <div className="billing-usage-grid">
          {Object.entries(data.entitlements.remaining).map(([metric, remaining]) => {
            const used = data.usage[metric] ?? 0;
            const limit = currentPlan?.monthly_limits[metric] ?? null;
            const ratio = limit && limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
            return (
              <div className="billing-usage-item" key={metric}>
                <div className="billing-usage-heading">
                  <span>{usageLabel(metric)}</span>
                  <strong>{remaining === null ? `${used.toLocaleString()} used` : `${used.toLocaleString()} / ${limit?.toLocaleString() ?? "—"}`}</strong>
                </div>
                <div className="billing-progress"><span style={{ width: `${ratio}%` }} /></div>
                <small>{remaining === null ? "No configured limit" : `${remaining.toLocaleString()} remaining`}</small>
              </div>
            );
          })}
        </div>
      </section>

      <section>
        <div className="billing-section-heading">
          <div><span className="eyebrow">AVAILABLE PLANS</span><h2>Choose a commercial tier</h2></div>
          <p>Pricing and limits are current product hypotheses and can change during validation.</p>
        </div>
        <div className="billing-plan-grid">
          {data.catalog.map((plan) => {
            const active = plan.plan_id === data.subscription.plan_id;
            return (
              <article className={`panel billing-card ${active ? "billing-card-active" : ""}`} key={plan.plan_id}>
                {active && <span className="billing-current-badge">Current plan</span>}
                <span className="eyebrow">{plan.name.toUpperCase()}</span>
                <h3>{planPrice(plan)}</h3>
                <p>{plan.max_seats} seats · {plan.max_workspaces} workspaces</p>
                <div className="billing-plan-limits">
                  {Object.entries(plan.monthly_limits).map(([metric, limit]) => (
                    <span key={metric}><strong>{limit?.toLocaleString() ?? "∞"}</strong> {usageLabel(metric).toLowerCase()}</span>
                  ))}
                </div>
                <button
                  type="button"
                  className={active ? "secondary-button" : "primary-button"}
                  disabled={active || !data.billing.checkout_ready || busyPlan !== null}
                  onClick={() => void startCheckout(plan.plan_id)}
                >
                  {active ? "Current plan" : busyPlan === plan.plan_id ? "Opening checkout…" : data.billing.checkout_ready ? "Upgrade" : "Checkout pending provider setup"}
                </button>
              </article>
            );
          })}
        </div>
      </section>

      <section className="billing-boundary">
        <strong>{data.billing.checkout_ready ? "Checkout is connected." : "Billing checkout is not connected yet."}</strong>
        <span>{data.billing.checkout_ready ? "Payment is handled by the configured provider. Your product access changes only after verified provider events update the organization state." : "The commercial plan catalog and usage state remain available while provider setup is pending."}</span>
      </section>
    </div>
  );
}
