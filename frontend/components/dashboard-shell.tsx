"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { Workspace } from "../lib/types";
import { getScopeValues, onboardDataset, resetSessionScope, updateSessionScope } from "../lib/api";
import { useAppState } from "../lib/app-state";
import { useAuth } from "../lib/auth";
import ActionWorkflowPanel from "./action-workflow-panel";

const nav: { id: Workspace | "decisions" | "forecast" | "billing"; label: string }[] = [
  { id: "decisions", label: "Decisions" },
  { id: "overview", label: "Overview" },
  { id: "forecast", label: "Forecast" },
  { id: "explore", label: "Explore" },
  { id: "insights", label: "Insights" },
  { id: "ask", label: "Ask Analyst" },
  { id: "actions", label: "Actions" },
  { id: "reports", label: "Reports" },
  { id: "monitoring", label: "Monitoring" },
  { id: "saved", label: "Saved" },
  { id: "billing", label: "Billing" },
];

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { state, dispatch } = useAppState();
  const { status, user, workspaceId, setWorkspaceId, signOut, addWorkspace } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scopeField, setScopeField] = useState<string>("");
  const [scopeValue, setScopeValue] = useState<string>("");
  const [scopeValues, setScopeValues] = useState<string[]>([]);
  const [scopeBusy, setScopeBusy] = useState(false);
  const [scopeError, setScopeError] = useState<string | null>(null);
  const [workspaceBusy, setWorkspaceBusy] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/");
  }, [status, router]);

  useEffect(() => {
    let active = true;
    const sessionId = state.session?.session_id;

    if (!sessionId || !scopeField) {
      setScopeValues([]);
      setScopeValue("");
      return () => { active = false; };
    }

    setScopeBusy(true);
    setScopeError(null);
    setScopeValues([]);
    setScopeValue("");

    getScopeValues(sessionId, scopeField)
      .then((values) => {
        if (!active) return;
        setScopeValues(values.map((item) => item.label));
      })
      .catch((err) => {
        if (!active) return;
        setScopeError(err instanceof Error ? err.message : "Scope values could not be loaded.");
      })
      .finally(() => {
        if (active) setScopeBusy(false);
      });

    return () => { active = false; };
  }, [scopeField, state.session?.session_id]);

  if (status === "loading") return <div className="auth-loading-screen">Checking your organization…</div>;
  if (status !== "authenticated" || !user) return null;

  const authenticatedUser = user;
  const readiness = !state.hydrated
    ? "hydrating"
    : state.loadingDataset
      ? "dataset-loading"
      : state.dataset && state.session
        ? "dataset-ready"
        : "workspace-ready";

  const allowed = new Set<string>(state.dataset?.capabilities.workspaces ?? nav.map((item) => item.id));
  const filterableFields = state.dataset?.semantic && "dimensions" in state.dataset.semantic && Array.isArray(state.dataset.semantic.dimensions) ? state.dataset.semantic.dimensions : [];

  async function handleUpload(file: File) {
    setError(null);
    setBusy(true);
    dispatch({ type: "dataset_loading" });
    try {
      if (!workspaceId) throw new Error("Choose a workspace before uploading data.");
      const result = await onboardDataset(file, workspaceId);
      dispatch({
        type: "dataset_loaded",
        dataset: result.dataset,
        session: {
          session_id: result.sessionId,
          dataset_id: result.dataset.dataset_id,
          organization_id: authenticatedUser.organization_id,
          workspace_id: workspaceId,
          scope: { filters: [] },
          active_analysis: null,
          comparison: null,
        },
        key: `${authenticatedUser.id}:${workspaceId}`,
      });
      router.replace("/dashboard/overview");
    } catch (err) {
      dispatch({ type: "dataset_reset" });
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function applyFilter() {
    if (!state.session || !scopeField || !scopeValue) return;
    setScopeBusy(true); setScopeError(null);
    try {
      const existing = state.session.scope.filters.filter(f => f.field !== scopeField);
      const updated = await updateSessionScope(state.session.session_id, [...existing, { field: scopeField, operator: "in", values: [scopeValue] }]);
      dispatch({ type: "session_updated", session: updated });
    } catch (err) { setScopeError(err instanceof Error ? err.message : "Scope could not be updated."); }
    finally { setScopeBusy(false); }
  }

  async function clearScope() {
    if (!state.session) return;
    setScopeBusy(true); setScopeError(null);
    try { const updated = await resetSessionScope(state.session.session_id); dispatch({ type: "session_updated", session: updated }); }
    catch (err) { setScopeError(err instanceof Error ? err.message : "Scope could not be reset."); }
    finally { setScopeBusy(false); }
  }

  return (
    <div className="app-frame" data-v4-readiness={readiness}>
      <aside className="sidebar">
        <Link href="/" className="brand" aria-label="Avenlytics home">
          <div className="brand-mark">AV</div>
          <div><strong>Avenlytics</strong><span>AI Sales Analyst</span></div>
        </Link>
        <nav className="nav-list" aria-label="Primary navigation">
          {nav.filter((item) => item.id === "decisions" || item.id === "forecast" || item.id === "billing" || allowed.has(item.id)).map((item) => {
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
          <div><span className="eyebrow">{authenticatedUser.organization_name}</span><strong>{authenticatedUser.workspace_name} · <span className="dataset-filename">{state.dataset?.file_name ?? "No dataset loaded"}</span></strong></div>
          <div className="topbar-actions">
            <div className="account-controls">
              <select aria-label="Workspace" value={workspaceId ?? ""} onChange={async (e) => {
                const next = e.target.value;
                if (!next || next === workspaceId) return;
                setWorkspaceId(next);
                dispatch({ type: "dataset_reset" });
                router.replace("/dashboard/overview");
              }}>
                {authenticatedUser.workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
              </select>
              <button type="button" className="text-button topbar-button" onClick={async () => {
                const name = window.prompt("New workspace name");
                if (!name?.trim() || workspaceBusy) return;
                setWorkspaceBusy(true);
                try { await addWorkspace(name.trim()); dispatch({ type: "dataset_reset" }); router.replace("/dashboard/overview"); }
                catch (err) { setError(err instanceof Error ? err.message : "Workspace could not be created."); }
                finally { setWorkspaceBusy(false); }
              }}>{workspaceBusy ? "Creating…" : "New workspace"}</button>
              <button type="button" className="text-button topbar-button" onClick={() => void signOut()}>Sign out</button>
            </div>
            {state.dataset?.business_model_label && <span className="badge">{state.dataset.business_model_label}</span>}
            <label className="upload-button">{busy ? "Analyzing…" : "Upload new data"}<input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])} disabled={busy} /></label>
          </div>
        </header>
        <div className="scope-strip">
          <span>Scope</span><strong>{state.session?.scope.filters.length ? state.session.scope.filters.map(f => `${f.field} = ${f.values.join(", ")}`).join(" · ") : "All data"}</strong>{state.dataset && <span>{state.dataset.row_count.toLocaleString()} rows · {state.dataset.column_count} fields</span>}
          <details className="scope-editor">
            <summary>Filter</summary>
            <div className="scope-editor-body">
              <select aria-label="Scope field" value={scopeField} onChange={e => setScopeField(e.target.value)} disabled={scopeBusy || !filterableFields.length}>
                <option value="">Choose field…</option>
                {filterableFields.map(field => <option key={field} value={field}>{field.replaceAll("_", " ")}</option>)}
              </select>
              <select aria-label="Scope value" value={scopeValue} onChange={e => setScopeValue(e.target.value)} disabled={scopeBusy || !scopeValues.length}>
                <option value="">Choose value…</option>
                {scopeValues.map(value => <option key={value} value={value}>{value}</option>)}
              </select>
              <button type="button" className="secondary-button" onClick={applyFilter} disabled={scopeBusy || !scopeField || !scopeValue}>{scopeBusy ? "Applying…" : "Apply"}</button>
              <button type="button" className="text-button" onClick={clearScope} disabled={scopeBusy || !(state.session?.scope.filters.length)}>Clear scope</button>
              {scopeError && <span className="error-text" role="alert">{scopeError}</span>}
            </div>
          </details>
        </div>
        {pathname === "/dashboard/actions" && state.dataset && <ActionWorkflowPanel datasetId={state.dataset.dataset_id} sessionId={state.session?.session_id} />}
        <section className="workspace">{children}</section>
      </main>
    </div>
  );
}
