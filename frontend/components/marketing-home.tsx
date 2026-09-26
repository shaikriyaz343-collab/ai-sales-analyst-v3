"use client";

import Link from "next/link";

const outcomes = [
  {
    eyebrow: "01 · WHAT CHANGED",
    title: "See the movement that matters",
    text: "Turn your latest sales export into a focused view of pipeline movement, momentum, and changes worth discussing.",
  },
  {
    eyebrow: "02 · WHY IT MATTERS",
    title: "Understand the signal",
    text: "Get evidence-backed context on the risks, opportunities, and trends behind the numbers.",
  },
  {
    eyebrow: "03 · WHAT NEXT",
    title: "Leave with an action",
    text: "Ask the analyst follow-ups, inspect the evidence, and carry the useful answer into the next revenue review.",
  },
];

const workflow = [
  { label: "UPLOAD", title: "Drop in your export", text: "CSV, Excel, or the sales export your team already trusts." },
  { label: "UNDERSTAND", title: "Get a revenue view", text: "The analyst organizes the current session around validated signals and forecast context." },
  { label: "ACT", title: "Ask, investigate, act", text: "Move from a headline to the underlying evidence and next business action." },
];

const faqs = [
  {
    question: "Do we need to replace our CRM?",
    answer: "No. Start with the sales data export you already use. The product is designed as an analyst layer, not a new system of record.",
  },
  {
    question: "What can the analyst answer?",
    answer: "It can summarize validated changes, investigate pipeline signals, answer questions about the current dataset, produce reports, and surface evidence behind its conclusions.",
  },
  {
    question: "Does the analyst invent numbers?",
    answer: "The product is designed to stay grounded in validated source data. When the evidence does not support an answer, the analyst surfaces that limitation instead of filling the gap with a made-up metric.",
  },
  {
    question: "How quickly can we get started?",
    answer: "Create an account, choose a workspace, upload a CSV or Excel export, and use the resulting analysis as the starting point for your revenue review.",
  },
];

export default function MarketingHome() {
  return (
    <main className="landing-v2-page">
      <header className="landing-v2-nav">
        <Link href="/" className="landing-v2-brand" aria-label="AI Sales Analyst home">
          <span className="landing-v2-mark">AI</span>
          <span>
            <strong>AI Sales Analyst</strong>
            <small>Your AI Revenue Analyst</small>
          </span>
        </Link>

        <nav className="landing-v2-nav-links" aria-label="Main navigation">
          <a href="#product">Product</a>
          <a href="#pricing">Pricing</a>
          <Link href="/login">Sign in</Link>
          <Link href="/login?mode=signup" className="landing-v2-nav-cta">Start free</Link>
        </nav>
      </header>

      <section className="landing-v2-hero">
        <div className="landing-v2-hero-copy">
          <span className="landing-v2-kicker">AI REVENUE ANALYST · BUILT FOR SALES TEAMS</span>
          <h1>Know what changed in your pipeline before the meeting starts.</h1>
          <p className="landing-v2-lede">
            Upload the sales data you already have. Get a grounded revenue view of what changed,
            why it matters, what the current data supports, and where to focus next.
          </p>

          <div className="landing-v2-actions">
            <Link href="/login?mode=signup" className="landing-v2-primary">Start your 14-day trial <span>→</span></Link>
            <a href="#product" className="landing-v2-secondary">See how it works</a>
          </div>

          <div className="landing-v2-proof-row">
            <span>CSV / Excel / CRM exports</span>
            <span>Evidence-first analysis</span>
            <span>No CRM replacement</span>
            <span>No implementation project</span>
          </div>
        </div>

        <div className="landing-v2-product-shell" aria-label="Illustrative AI Sales Analyst workspace preview">
          <div className="landing-v2-product-window">
            <div className="landing-v2-window-top">
              <div className="landing-v2-window-dots"><i /><i /><i /></div>
              <span>AI SALES ANALYST</span>
              <span className="landing-v2-live-badge">ANALYSIS READY</span>
            </div>

            <div className="landing-v2-window-body">
              <aside className="landing-v2-mini-sidebar">
                <div className="landing-v2-mini-brand">AI</div>
                <span className="active">Decisions</span>
                <span>Forecast</span>
                <span>Ask Analyst</span>
                <span>Reports</span>
              </aside>

              <div className="landing-v2-dashboard">
                <div className="landing-v2-dashboard-head">
                  <div>
                    <span className="landing-v2-mini-label">DECISION COCKPIT</span>
                    <h2>What deserves attention now?</h2>
                    <p>Validated signals from the current sales dataset.</p>
                  </div>
                  <div className="landing-v2-grounded">
                    <b>●</b> DATA GROUNDED
                  </div>
                </div>

                <div className="landing-v2-signal-grid">
                  <article>
                    <span>WHAT CHANGED</span>
                    <strong>Pipeline movement</strong>
                    <p>Compare current performance with source evidence.</p>
                  </article>
                  <article>
                    <span>WHY IT MATTERS</span>
                    <strong>Risk is concentrated</strong>
                    <p>Inspect the signals that can affect the next review.</p>
                  </article>
                  <article>
                    <span>WHAT NEXT</span>
                    <strong>Recommended action</strong>
                    <p>Move from insight to an evidence-backed follow-up.</p>
                  </article>
                </div>

                <div className="landing-v2-question">
                  <div>
                    <span>ASK THE ANALYST</span>
                    <strong>“What changed in pipeline quality this period?”</strong>
                  </div>
                  <span className="landing-v2-arrow">↗</span>
                </div>
              </div>
            </div>
          </div>
          <div className="landing-v2-product-note">Illustrative workspace · actual answers use your validated data</div>
        </div>
      </section>

      <section className="landing-v2-proof-band">
        <div>
          <span>BUILT FOR THE WEEKLY REVENUE RHYTHM</span>
          <strong>Less spreadsheet archaeology. More time deciding.</strong>
        </div>
        <div className="landing-v2-proof-metrics">
          <span><b>Upload</b> your latest export</span>
          <span><b>Understand</b> the current signal</span>
          <span><b>Act</b> on what the evidence supports</span>
        </div>
      </section>

      <section id="product" className="landing-v2-section">
        <div className="landing-v2-section-intro">
          <span className="landing-v2-kicker">THE ANALYST LAYER</span>
          <h2>From raw sales export to a decision-ready revenue view.</h2>
          <p>
            The product is deliberately focused: make the next revenue conversation easier to prepare,
            easier to explain, and easier to act on.
          </p>
        </div>

        <div className="landing-v2-outcome-grid">
          {outcomes.map((outcome) => (
            <article key={outcome.eyebrow} className="landing-v2-outcome-card">
              <span>{outcome.eyebrow}</span>
              <h3>{outcome.title}</h3>
              <p>{outcome.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-v2-section landing-v2-workflow">
        <div className="landing-v2-section-intro compact">
          <span className="landing-v2-kicker">HOW IT WORKS</span>
          <h2>One simple loop.</h2>
        </div>

        <div className="landing-v2-workflow-grid">
          {workflow.map((step, index) => (
            <article key={step.label} className="landing-v2-workflow-card">
              <div className="landing-v2-workflow-number">0{index + 1}</div>
              <span>{step.label}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-v2-section landing-v2-capabilities">
        <div className="landing-v2-capability-copy">
          <span className="landing-v2-kicker">WHAT YOU GET</span>
          <h2>One analyst layer across the work your revenue review already needs.</h2>
          <p>Keep the systems you already use. Add one place to investigate the current sales picture.</p>
        </div>

        <div className="landing-v2-capability-list">
          <div><b>Decisions</b><span>Prioritized, validated risks, opportunities, and changes.</span></div>
          <div><b>Forecast</b><span>Context for what the current pipeline supports.</span></div>
          <div><b>Ask Analyst</b><span>Plain-English questions tied to the current workspace.</span></div>
          <div><b>Reports</b><span>Turn the current analysis into a review-ready output.</span></div>
        </div>
      </section>

      <section className="landing-v2-section landing-v2-pricing-section" id="pricing">
        <div className="landing-v2-section-intro">
          <span className="landing-v2-kicker">PRICING</span>
          <h2>Start with a sales team. Expand when the workflow sticks.</h2>
          <p>Both plans include the same core analyst experience. Higher tiers increase the workspace and usage limits.</p>
        </div>

        <div className="landing-v2-price-grid">
          <article className="landing-v2-price-card">
            <div className="landing-v2-price-top">
              <span>STARTER</span>
              <span>For focused teams</span>
            </div>
            <div className="landing-v2-price">$49 <small>/ month</small></div>
            <p>For a small revenue team building a repeatable analysis workflow.</p>
            <Link href="/login?mode=signup" className="landing-v2-price-button">Start free</Link>
          </article>

          <article className="landing-v2-price-card featured">
            <div className="landing-v2-price-top">
              <span>GROWTH</span>
              <span>For expanding teams</span>
            </div>
            <div className="landing-v2-price">$149 <small>/ month</small></div>
            <p>For growing teams that need more analysis, monitoring, reporting, and saved intelligence.</p>
            <Link href="/login?mode=signup" className="landing-v2-price-button filled">Start free</Link>
          </article>
        </div>

        <div className="landing-v2-trial-note">14-day trial · No CRM migration · No implementation project</div>
      </section>

      <section className="landing-v2-section landing-v2-faq">
        <div className="landing-v2-section-intro compact">
          <span className="landing-v2-kicker">QUESTIONS</span>
          <h2>What teams usually want to know first.</h2>
        </div>

        <div className="landing-v2-faq-list">
          {faqs.map((faq) => (
            <details key={faq.question}>
              <summary>{faq.question}<span>+</span></summary>
              <p>{faq.answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="landing-v2-final">
        <div>
          <span className="landing-v2-kicker">READY FOR THE NEXT REVENUE REVIEW?</span>
          <h2>Give your sales data an analyst.</h2>
          <p>Start with the export you already have. See what the data supports. Take the useful answer into the next meeting.</p>
        </div>
        <Link href="/login?mode=signup" className="landing-v2-final-button">Start your 14-day trial <span>→</span></Link>
      </section>

      <footer className="landing-v2-footer">
        <span>AI Sales Analyst</span>
        <span>Decision intelligence for sales teams</span>
      </footer>
    </main>
  );
}
