"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../lib/auth";

export default function AuthScreen({ initialMode = "signin" }: { initialMode?: "signin" | "signup" }) {
  const { signIn, signUp } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">(initialMode);

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "signin") await signIn(email, password);
      else await signUp(email, password, name, organizationName);
      router.replace("/dashboard/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-shell">
        <Link href="/" className="auth-back-link">← Back to Avelyntics</Link>
        <header className="onboarding-brand">
          <div className="brand-mark">A</div>
          <div><strong>Avelyntics</strong><span>AI Sales Analyst · No CRM replacement</span></div>
        </header>
        <section className="auth-marketing" aria-labelledby="public-value-proposition">
          <span className="eyebrow">AVELyntics · AI REVENUE ANALYST</span>
          <h1 id="public-value-proposition">Know what changed in your pipeline before the meeting starts.</h1>
          <p>Upload your sales export and Avelyntics will calculate an evidence-backed revenue story from the validated dataset: what changed, why it matters, what the forecast says, and what your team should do next.</p>
          <div className="auth-value-grid">
            <div><strong>What changed</strong><span>See the movements that matter.</span></div>
            <div><strong>Why it matters</strong><span>Trace each conclusion to source data.</span></div>
            <div><strong>What next</strong><span>Turn signals into actions and monitoring.</span></div>
          </div>
        </section>
        <section className="auth-card panel">
          <div>
            <span className="eyebrow">YOUR ANALYST WORKSPACE</span>
            <h1>{mode === "signin" ? "Welcome back." : "Create your analyst workspace."}</h1>
            <p>{mode === "signin" ? "Sign in to continue to your organization and its business workspaces." : "Upload your sales data and get the revenue story, evidence-backed risks, forecast, and next actions — without replacing your CRM."}</p>
          </div>
          <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
            <button type="button" role="tab" aria-selected={mode === "signin"} className={mode === "signin" ? "selected" : ""} onClick={() => setMode("signin")}>Sign in</button>
            <button type="button" role="tab" aria-selected={mode === "signup"} className={mode === "signup" ? "selected" : ""} onClick={() => setMode("signup")}>Create account</button>
          </div>
          <form onSubmit={submit} className="auth-form">
            {mode === "signup" && <>
              <label>Full name<input aria-label="Full name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required /></label>
              <label>Organization name<input aria-label="Organization name" value={organizationName} onChange={(e) => setOrganizationName(e.target.value)} placeholder="Acme Revenue Team" /></label>
            </>}
            <label>Email<input aria-label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
            <label>Password<input aria-label="Password" type="password" autoComplete={mode === "signin" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} minLength={10} required /></label>
            {error && <div className="onboarding-error" role="alert">{error}</div>}
            <button type="submit" className="primary-button" disabled={busy}>{busy ? "Working…" : mode === "signin" ? "Sign in" : "Create account"}</button>
          </form>
          <div className="auth-trust"><strong>Private by default · Data-grounded by design.</strong><span>Your organization, users, datasets and saved intelligence are isolated by account. Unsupported questions are surfaced rather than guessed.</span></div>
        </section>
      </div>
    </main>
  );
}
