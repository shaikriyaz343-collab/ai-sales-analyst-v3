import Link from "next/link";

export const AVENLYTICS_LEGAL_NAME = "Avenlytics";
export const AVENLYTICS_SUPPORT_EMAIL = "shaikriyaz343@gmail.com";
export const LAST_UPDATED = "September 28, 2026";

type LegalSection = {
  title: string;
  paragraphs?: string[];
  items?: string[];
};

export default function LegalPage({
  label,
  title,
  intro,
  sections,
}: {
  label: string;
  title: string;
  intro: string;
  sections: LegalSection[];
}) {
  return (
    <main className="legal-page">
      <div className="legal-shell">
        <header className="legal-header">
          <Link href="/" className="legal-brand" aria-label="Avenlytics home">
            <span className="legal-mark">A</span>
            <span>
              <strong>{AVENLYTICS_LEGAL_NAME}</strong>
              <small>AI Sales Analyst · Revenue intelligence</small>
            </span>
          </Link>
          <Link href="/" className="legal-back">Back to Avenlytics</Link>
        </header>

        <article className="legal-card">
          <div className="legal-heading">
            <span className="legal-eyebrow">{label}</span>
            <h1>{title}</h1>
            <p>{intro}</p>
            <small>Last updated: {LAST_UPDATED}</small>
          </div>

          <div className="legal-content">
            {sections.map((section) => (
              <section key={section.title}>
                <h2>{section.title}</h2>
                {section.paragraphs?.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
                {section.items && (
                  <ul>
                    {section.items.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                )}
              </section>
            ))}
          </div>

          <div className="legal-contact">
            Questions about these terms or policies? Contact <a href={`mailto:${AVENLYTICS_SUPPORT_EMAIL}`}>{AVENLYTICS_SUPPORT_EMAIL}</a>.
          </div>
        </article>

        <footer className="legal-footer">
          <span>{AVENLYTICS_LEGAL_NAME}</span>
          <nav aria-label="Legal">
            <Link href="/terms">Terms</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/refunds">Refunds</Link>
          </nav>
        </footer>
      </div>
    </main>
  );
}
