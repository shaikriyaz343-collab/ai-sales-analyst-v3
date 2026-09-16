"use client";

import { useEffect, useState } from "react";
import { getActions, updateActionStatus } from "../lib/api";
import type { ActionItem, ActionsResponse } from "../lib/types";

const STATUSES = [
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "done", label: "Done" },
  { value: "blocked", label: "Blocked" },
];

export default function ActionWorkflowPanel({ datasetId, sessionId }: { datasetId: string; sessionId?: string }) {
  const [data, setData] = useState<ActionsResponse | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (!sessionId) {
      setData(null);
      return () => { active = false; };
    }
    setError(null);
    getActions(datasetId, sessionId)
      .then((result) => { if (active) setData(result); })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : "Action workflow could not be loaded."); });
    return () => { active = false; };
  }, [datasetId, sessionId]);

  async function setStatus(action: ActionItem, status: string) {
    if (!sessionId || busy === action.id || action.status === status) return;
    setBusy(action.id);
    setError(null);
    try {
      const updated = await updateActionStatus(datasetId, sessionId, action.id, status);
      setData((current) => current ? { ...current, actions: current.actions.map((item) => item.id === updated.id ? updated : item) } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action status could not be updated.");
    } finally {
      setBusy(null);
    }
  }

  if (!sessionId || !data) return null;

  const open = data.actions.filter((action) => action.status === "open").length;
  const inProgress = data.actions.filter((action) => action.status === "in_progress").length;
  const done = data.actions.filter((action) => action.status === "done").length;
  const blocked = data.actions.filter((action) => action.status === "blocked").length;

  return (
    <section className="panel action-workflow-panel" aria-label="Action workflow">
      <div className="section-heading">
        <div>
          <span className="eyebrow">USER-CONTROLLED WORKFLOW</span>
          <h3>Track recommended actions</h3>
        </div>
        <span className="section-kicker">Persistent</span>
      </div>
      <p>Status changes are saved to the active analysis session and remain visible when the Actions workspace is reopened.</p>
      <div className="workflow-summary" aria-label="Action status summary">
        <span>Open {open}</span>
        <span>In progress {inProgress}</span>
        <span>Done {done}</span>
        <span>Blocked {blocked}</span>
      </div>
      <div className="workflow-list">
        {data.actions.map((action) => (
          <div className="workflow-row" key={action.id}>
            <div>
              <strong>{action.title}</strong>
              <small>{action.priority} priority · {action.owner}</small>
            </div>
            <select
              aria-label={`Status for ${action.title}`}
              value={action.status}
              onChange={(event) => void setStatus(action, event.target.value)}
              disabled={busy === action.id}
            >
              {STATUSES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>
        ))}
      </div>
      {error && <p className="error-text" role="alert">{error}</p>}
    </section>
  );
}
