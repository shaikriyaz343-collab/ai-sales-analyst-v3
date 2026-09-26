"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { onboardDataset } from "../lib/api";
import { useAppState } from "../lib/app-state";
import { useAuth } from "../lib/auth";

const ACCEPT = ".csv,.xlsx,.xls";

export default function OnboardingScreen() {
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { dispatch } = useAppState();
  const { workspaceId, user } = useAuth();
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function processFile(file: File | undefined) {
    if (!file || busy) return;
    const lower = file.name.toLowerCase();
    if (!lower.endsWith(".csv") && !lower.endsWith(".xlsx") && !lower.endsWith(".xls")) {
      setError("Please upload a CSV, XLSX, or XLS file.");
      return;
    }
    setError(null);
    setBusy(true);
    dispatch({ type: "dataset_loading" });
    try {
      if (!workspaceId) throw new Error("Choose a workspace before uploading data.");
      const result = await onboardDataset(file, workspaceId);
      dispatch({ type: "dataset_loaded", dataset: result.dataset, session: { session_id: result.sessionId, dataset_id: result.dataset.dataset_id, organization_id: user?.organization_id, workspace_id: workspaceId, scope: { filters: [] }, active_analysis: null, comparison: null }, key: user && workspaceId ? `${user.id}:${workspaceId}` : "" });
      router.push("/dashboard/overview");
    } catch (err) {
      dispatch({ type: "dataset_reset" });
      setError(err instanceof Error ? err.message : "We could not understand this file.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <main className="onboarding-page">
      <div className="onboarding-shell">
        <header className="onboarding-brand">
          <div className="brand-mark">A</div>
          <div><strong>Avenlytics</strong><span>AI Sales Analyst · Decision intelligence</span></div>
        </header>

        <section className="onboarding-account-bar"><span>{user?.organization_name ?? "Organization"}</span><span>{user?.workspace_name ?? "Workspace"}</span></section>

        <section className="onboarding-hero">
          <div className="hero-copy">
            <span className="eyebrow">FROM DATA TO DECISIONS</span>
            <h1>Turn your sales data into a clear business story.</h1>
            <p>Upload a CSV or Excel file. Avenlytics will understand the business model, validate available signals, and prepare an analyst workspace grounded in your data.</p>
          </div>

          <button
            type="button"
            className={`dropzone ${dragging ? "dragging" : ""}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); void processFile(event.dataTransfer.files?.[0]); }}
            disabled={busy}
          >
            <input ref={inputRef} type="file" accept={ACCEPT} onChange={(event) => void processFile(event.target.files?.[0])} hidden />
            <div className="upload-icon">↑</div>
            <strong>{busy ? "Understanding your business…" : "Upload your CSV or Excel file"}</strong>
            <span>{busy ? "Profiling fields, business model and data quality" : "Drag and drop here, or click to browse"}</span>
            <small>CSV · XLSX · XLS</small>
          </button>
        </section>

        {error && <div className="onboarding-error" role="alert">{error}</div>}

        <section className="onboarding-trust">
          <div><span>01</span><strong>Understand</strong><p>Fields, business model and data quality.</p></div>
          <div><span>02</span><strong>Validate</strong><p>Only supported analytics become available.</p></div>
          <div><span>03</span><strong>Analyze</strong><p>Evidence-backed insights and actions follow.</p></div>
        </section>

        <footer className="onboarding-footer">
          <span>No fabricated numbers. Deterministic metrics. Evidence-backed analysis.</span>
          <span>Your existing data remains the source of truth.</span>
        </footer>
      </div>
    </main>
  );
}
