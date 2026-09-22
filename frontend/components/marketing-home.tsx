"use client";

import Link from "next/link";

const workflow = [
  {
    number: "01",
    title: "Drop in your latest export",
    text: "Start with the CSV or Excel file your team already uses. No CRM migration, warehouse project, or implementation sprint.",
  },
  {
    number: "02",
    title: "See the revenue story",
    text: "Turn the source data into a decision view: what changed, why it matters, where risk is building, and what the data supports.",
  },
  {
    number: "03",
    title: "Keep the signal",
    text: "Ask follow-up questions, save important findings, monitor changes, and carry the useful evidence into the next review.",
  },
];

const signalCards = [
  { label: "WHAT CHANGED", value: "Pipeline movement", text: "Compare the current period with the evidence in your source data." },
  { label: "WHY IT MATTERS", value: "Concentrated risk", text: "Surface the changes most likely to affect the next revenue review." },
  { label: "WHAT NEXT", value: "Priority actions", text: "Give the team a clear next step instead of another spreadsheet." },
];

export default function MarketingHome() {
  return (
    <main className="marketing-page">
      <header className="marketing-nav">
        <Link href="/" className="marketing-brand" aria-label="AI Sales Analyst home">
          <span className="brand-mark">AI</span>
          <span>
            <strong>AI Sales Analyst</strong>
            <small>Your AI Revenue Analyst</small>
          </span>
        </Link>

        <nav className="marketing-nav-links" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#who-its-for">Who it&apos;s for</a>
          <a href="#pricing">Pricing</a>
          <Link href="/login">Sign in</Link>
          <Link href="/login?mode=signup" className="marketing-nav-cta">Start free</Link>
        </nav>
      </header>

      <section className="marketing-hero">
        <div className="marketing-hero-copy">
          <span className="eyebrow">AI REVENUE ANALYST</span>
          <h1>Walk into the next revenue meeting knowing what changed.</h1>
          <p className="marketing-lede">
            Upload a sales export and get a grounded operating view of your pipeline:
            what changed, why it matters, what the current data supports for the forecast,
            and where the team should focus next.
          </p>

          <div className="marketing-actions">
            <Link href="/login?mode=signup" className="primary-button marketing-primary">
              Start your 14-day trial
            </Link>
            <Link href="/login" className="secondary-button marketing-secondary">
              Sign in
            </Link>
          </div>

          <p className="marketing-proof">
            No CRM replacement. No implementation project. No fabricated numbers.
          </p>
        </div>

        <div className="marketing-console" aria-label="Illustration of the AI Revenue Analyst workflow">
          <div className="marketing-console-top">
            <span>REVENUE BRIEF</span>
            <span className="marketing-status-pill">DATA GROUNDED</span>
          </div>

          <div className="marketing-console-main">
            <div className="marketing-metric">
              <span>THIS WEEK&apos;S SIGNAL</span>
              <strong>Know what deserves attention.</strong>
              <small>
                A decision-ready view built from the evidence already sitting in your sales data.
              </small>
            </div>

            <div className="marketing-evidence">
              {signalCards.map((card) => (
                <div key={card.label} className="marketing-evidence-row">
                  <span>✓</span>
                  <p>
                    <strong>{card.label}</strong>
                    <br />
                    {card.value} — {card.text}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="marketing-console-footer">
            <span>Evidence</span>
            <span>Forecast</span>
            <span>Attention</span>
            <span>Action</span>
          </div>
        </div>
      </section>

      <section className="marketing-section" id="how-it-works">
        <div className="marketing-section-heading">
          <span className="eyebrow">FROM DATA TO DECISIONS</span>
          <h2>One workflow from export to next action.</h2>
          <p>
            Keep the systems you already use. Add an analyst layer that turns routine sales
            review into a faster decision loop.
          </p>
        </div>

        <div className="marketing-workflow-grid">
          {workflow.map((step) => (
            <article className="marketing-step panel" key={step.number}>
              <span>{step.number}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="marketing-section marketing-audience" id="who-its-for">
        <div className="marketing-audience-copy">
          <span className="eyebrow">BUILT FOR SALES-LED TEAMS</span>
          <h2>For teams with data, pipeline, and too little analyst time.</h2>
          <p>
            Start with founder-led and manager-led B2B teams that already review revenue every
            week and want reliable answers without a long RevOps implementation.
          </p>
        </div>

        <div className="marketing-audience-list">
          <div>
            <strong>5–30 sellers</strong>
            <span>Enough activity and pipeline to benefit from a dedicated analyst layer.</span>
          </div>
          <div>
            <strong>CSV, Excel, or CRM exports</strong>
            <span>Use the source you have instead of changing your system of record.</span>
          </div>
          <div>
            <strong>Founder, Head of Sales, or COO</strong>
            <span>A clear owner who needs useful answers before the next revenue review.</span>
          </div>
        </div>
      </section>

      <section className="marketing-section marketing-pricing" id="pricing">
        <div className="marketing-section-heading">
          <span className="eyebrow">SIMPLE ACCOUNT-LEVEL PRICING</span>
          <h2>Start small. Upgrade when the workflow becomes part of the rhythm.</h2>
        </div>

        <div className="marketing-price-grid">
          <article className="marketing-price-card panel">
            <span className="eyebrow">STARTER</span>
            <div className="marketing-price">$49<span>/month</span></div>
            <p>For a focused sales team building a repeatable decision workflow.</p>
            <Link href="/login?mode=signup" className="secondary-button">
              Start trial
            </Link>
          </article>

          <article className="marketing-price-card panel marketing-price-featured">
            <span className="eyebrow">GROWTH</span>
            <div className="marketing-price">$149<span>/month</span></div>
            <p>For growing teams that need more questions, reports, monitoring, and saved intelligence.</p>
            <Link href="/login?mode=signup" className="primary-button">
              Start trial
            </Link>
          </article>
        </div>

        <p className="marketing-pricing-note">
          14-day trial. Billing is handled after you activate a paid plan.
        </p>
      </section>

      <section className="marketing-final-cta">
        <div>
          <span className="eyebrow">READY FOR THE NEXT REVENUE REVIEW?</span>
          <h2>Give your sales data an analyst.</h2>
          <p>Start with one export. Find one useful decision. Build from there.</p>
        </div>
        <Link href="/login?mode=signup" className="primary-button marketing-primary">
          Start free
        </Link>
      </section>

      <footer className="marketing-footer">
        <span>AI Sales Analyst</span>
        <span>Your AI Revenue Analyst · No CRM replacement</span>
      </footer>
    </main>
  );
}
