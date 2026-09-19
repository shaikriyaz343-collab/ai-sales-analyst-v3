"use client";

import Link from "next/link";

const workflow = [
  { number: "01", title: "Upload your sales data", text: "Start with the CSV or Excel export you already use. No CRM migration or warehouse project." },
  { number: "02", title: "Get the revenue story", text: "See what changed, why it matters, where risk is building, and what the current data supports." },
  { number: "03", title: "Act with evidence", text: "Ask questions, save useful intelligence, monitor signals, and turn findings into the next business action." },
];

const questions = [
  "What changed this month?",
  "Which pipeline risks need attention?",
  "What does the current data support for the forecast?",
];

export default function MarketingHome() {
  return (
    <main className="marketing-page">
      <header className="marketing-nav">
        <Link href="/" className="marketing-brand" aria-label="AI Sales Analyst home">
          <span className="brand-mark">AI</span>
          <span><strong>AI Sales Analyst</strong><small>Your AI Revenue Analyst</small></span>
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
          <h1>Know what changed in your pipeline before the meeting starts.</h1>
          <p className="marketing-lede">Upload your sales export and get an evidence-backed revenue story: what changed, why it matters, what the current data supports for the forecast, and what your team should do next.</p>
          <div className="marketing-actions">
            <Link href="/login?mode=signup" className="primary-button marketing-primary">Start your 14-day trial</Link>
            <Link href="/login" className="secondary-button marketing-secondary">Sign in</Link>
          </div>
          <p className="marketing-proof">No CRM replacement. No implementation project. No fabricated numbers.</p>
        </div>

        <div className="marketing-console" aria-label="Illustration of the AI Revenue Analyst workflow">
          <div className="marketing-console-top">
            <span>REVENUE BRIEF</span><span className="marketing-status-pill">DATA GROUNDED</span>
          </div>
          <div className="marketing-console-main">
            <div className="marketing-metric">
              <span>Pipeline signal</span>
              <strong>What changed</strong>
              <small>Compare current performance with the evidence in your source data.</small>
            </div>
            <div className="marketing-evidence">
              {questions.map((question) => (
                <div key={question} className="marketing-evidence-row"><span>✓</span><p>{question}</p></div>
              ))}
            </div>
          </div>
          <div className="marketing-console-footer"><span>Evidence</span><span>Forecast</span><span>Attention</span><span>Action</span></div>
        </div>
      </section>

      <section className="marketing-section" id="how-it-works">
        <div className="marketing-section-heading">
          <span className="eyebrow">FROM DATA TO DECISIONS</span>
          <h2>One clear workflow for the questions revenue leaders keep asking.</h2>
          <p>Keep the systems you already use. Add an analyst layer that turns sales data into a decision-ready operating view.</p>
        </div>
        <div className="marketing-workflow-grid">
          {workflow.map((step) => (
            <article className="marketing-step panel" key={step.number}>
              <span>{step.number}</span><h3>{step.title}</h3><p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="marketing-section marketing-audience" id="who-its-for">
        <div className="marketing-audience-copy">
          <span className="eyebrow">BUILT FOR SALES-LED TEAMS</span>
          <h2>For teams that already have sales data, but not enough analyst time.</h2>
          <p>Start with founder-led and manager-led B2B teams that review pipeline every week, work from a CRM or spreadsheet export, and want answers without a long RevOps implementation.</p>
        </div>
        <div className="marketing-audience-list">
          <div><strong>5–30 sellers</strong><span>Enough activity and pipeline to benefit from a dedicated analyst layer.</span></div>
          <div><strong>CSV, Excel or CRM exports</strong><span>Use the data you already have instead of changing your system of record.</span></div>
          <div><strong>Founder, Head of Sales or COO</strong><span>A clear owner who needs reliable answers before the next revenue review.</span></div>
        </div>
      </section>

      <section className="marketing-section marketing-pricing" id="pricing">
        <div className="marketing-section-heading">
          <span className="eyebrow">SIMPLE ACCOUNT-LEVEL PRICING</span>
          <h2>Start small. Upgrade when the analyst becomes part of the rhythm.</h2>
        </div>
        <div className="marketing-price-grid">
          <article className="marketing-price-card panel">
            <span className="eyebrow">STARTER</span><div className="marketing-price">$49<span>/month</span></div>
            <p>For a focused sales team building a repeatable weekly decision workflow.</p>
            <Link href="/login?mode=signup" className="secondary-button">Start trial</Link>
          </article>
          <article className="marketing-price-card panel marketing-price-featured">
            <span className="eyebrow">GROWTH</span><div className="marketing-price">$149<span>/month</span></div>
            <p>For growing teams that need more questions, reports, monitoring and saved intelligence.</p>
            <Link href="/login?mode=signup" className="primary-button">Start trial</Link>
          </article>
        </div>
        <p className="marketing-pricing-note">14-day trial. Billing is handled after you activate a paid plan.</p>
      </section>

      <section className="marketing-final-cta">
        <div><span className="eyebrow">READY FOR THE NEXT REVENUE REVIEW?</span><h2>Give your sales data an analyst.</h2><p>Start with one export. Find one useful decision. Build from there.</p></div>
        <Link href="/login?mode=signup" className="primary-button marketing-primary">Start free</Link>
      </section>

      <footer className="marketing-footer"><span>AI Sales Analyst</span><span>Your AI Revenue Analyst · No CRM replacement</span></footer>
    </main>
  );
}
