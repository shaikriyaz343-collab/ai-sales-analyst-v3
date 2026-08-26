"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import type { Workspace } from "../lib/types";
import { onboardDataset } from "../lib/api";
import { useAppState } from "../lib/app-state";

const nav: { id: Workspace; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "explore", label: "Explore" },
  { id: "insights", label: "Insights" },
  { id: "ask", label: "Ask Analyst" },
  { id: "actions", label: "Actions" },
  { id: "reports", label: "Reports" },
];

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { state, dispatch } = useAppState();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allowed = new Set(state.dataset?.capabilities.workspaces ?? nav.map((item) => item.id));

  async function handleUpload(file: File) {
    setError(null);
    setBusy(true);
    dispatch({ type: "dataset_loading" });
    try {
      const dataset = await onboardDataset(file);
      dispatch({ type: "dataset_loaded", dataset });
      router.replace("/dashboard/overview");
    } catch (err) {
      dispatch({ type: "dataset_reset" });
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link href="/" className="brand" aria-label="AI Sales Analyst home">
          <div className="brand-mark">AI</div>
          <div><strong>Sales Analyst</strong><span>Decision Intelligence</span></div>
        </Link>
        <nav className="nav-list" aria-label="Primary navigation">
          {nav.filter((item) => allowed.has(item.id)).map((item) => {
            const active = pathname === `/dashboard/${item.id}`;
            return <Link key={item.id} href={`/dashboard/${item.id}`} className={`nav-item ${active ? "active" : ""}`}>{item.label}</Link>;
          })}
        </nav>
        <div className="sidebar-footer">
          <label className="upload-mini">
            <span>{busy ? "Understanding…" : "Replace dataset"}</span>
            <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])} disabled={busy} />
          </label>
          {error && <p className="error-text" role="alert">{error}</p>}
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div><span className="eyebrow">DATASET</span><strong>{state.dataset?.file_name ?? "No dataset loaded"}</strong></div>
          <div className="topbar-actions">
            {state.dataset?.business_model_label && <span className="badge">{state.dataset.business_model_label}</span>}
            <label className="upload-button">{busy ? "Analyzing…" : "Upload new data"}<input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])} disabled={busy} /></label>
          </div>
        </header>
        <div className="scope-strip">
          <span>Scope</span><strong>All data</strong>{state.dataset && <span>{state.dataset.row_count.toLocaleString()} rows · {state.dataset.column_count} fields</span>}
        </div>
        <section className="workspace">{children}</section>
      </main>
    </div>
  );
}
