"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../lib/auth";

export default function AuthScreen() {
  const { signIn, signUp } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
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
        <header className="onboarding-brand">
          <div className="brand-mark">AI</div>
          <div><strong>AI Sales Analyst</strong><span>Decision intelligence for revenue teams</span></div>
        </header>
        <section className="auth-card panel">
          <div>
            <span className="eyebrow">YOUR ANALYST WORKSPACE</span>
            <h1>{mode === "signin" ? "Welcome back." : "Create your analyst workspace."}</h1>
            <p>{mode === "signin" ? "Sign in to continue to your organization and its business workspaces." : "Start with a private organization and a workspace ready for your business data."}</p>
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
          <div className="auth-trust"><strong>Private by default.</strong><span>Your organization, users, datasets and saved intelligence are isolated by account.</span></div>
        </section>
      </div>
    </main>
  );
}
