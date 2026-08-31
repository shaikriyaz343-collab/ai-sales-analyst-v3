"use client";

import { createContext, useContext, useEffect, useMemo, useReducer, useRef } from "react";
import type { AnalysisSession, DatasetSummary } from "./types";
import { createSession, getDataset, getSession } from "./api";
import { useAuth } from "./auth";

type State = {
  dataset: DatasetSummary | null;
  session: AnalysisSession | null;
  loadingDataset: boolean;
  hydrated: boolean;
  hydrationKey: string | null;
};

type Action =
  | { type: "hydration_started"; key: string }
  | { type: "dataset_loaded"; dataset: DatasetSummary; session: AnalysisSession; key: string }
  | { type: "dataset_loading" }
  | { type: "session_updated"; session: AnalysisSession }
  | { type: "dataset_reset"; key?: string };

const initialState: State = { dataset: null, session: null, loadingDataset: false, hydrated: false, hydrationKey: null };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "hydration_started":
      return { dataset: null, session: null, loadingDataset: true, hydrated: false, hydrationKey: action.key };
    case "dataset_loaded":
      return { dataset: action.dataset, session: action.session, loadingDataset: false, hydrated: true, hydrationKey: action.key };
    case "dataset_loading":
      return { ...state, dataset: null, session: null, loadingDataset: true, hydrated: state.hydrated };
    case "session_updated":
      return { ...state, session: action.session, hydrated: true };
    case "dataset_reset":
      return { ...initialState, hydrated: true, hydrationKey: action.key ?? state.hydrationKey };
    default:
      return state;
  }
}

const DATASET_PREFIX = "ai-sales-analyst-v4-dataset";
const SESSION_PREFIX = "ai-sales-analyst-v4-session";
const AppStateContext = createContext<{ state: State; dispatch: React.Dispatch<Action> } | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { status, user, workspaceId } = useAuth();
  const requestRef = useRef(0);
  const ownerKey = status === "authenticated" && user && workspaceId ? `${user.id}:${workspaceId}` : null;

  useEffect(() => {
    const requestId = ++requestRef.current;
    if (status === "loading") return;
    if (!ownerKey || !workspaceId) {
      dispatch({ type: "dataset_reset" });
      return;
    }

    const authOwnerKey = ownerKey;
    const authWorkspaceId = workspaceId;
    const datasetKey = `${DATASET_PREFIX}:${authOwnerKey}`;
    const sessionKey = `${SESSION_PREFIX}:${authOwnerKey}`;
    dispatch({ type: "hydration_started", key: authOwnerKey });

    async function hydrate() {
      const sessionId = window.localStorage.getItem(sessionKey);
      const datasetId = window.localStorage.getItem(datasetKey);
      try {
        if (sessionId) {
          const session = await getSession(sessionId);
          if (requestRef.current !== requestId || session.workspace_id !== authWorkspaceId) return;
          const dataset = await getDataset(session.dataset_id);
          if (requestRef.current !== requestId) return;
          dispatch({ type: "dataset_loaded", dataset, session, key: authOwnerKey });
          return;
        }
        if (!datasetId) {
          if (requestRef.current === requestId) dispatch({ type: "dataset_reset", key: authOwnerKey });
          return;
        }
        const dataset = await getDataset(datasetId);
        if (requestRef.current !== requestId) return;
        const session = await createSession(datasetId, authWorkspaceId);
        if (requestRef.current !== requestId) return;
        dispatch({ type: "dataset_loaded", dataset, session, key: authOwnerKey });
      } catch {
        if (requestRef.current === requestId) {
          window.localStorage.removeItem(datasetKey);
          window.localStorage.removeItem(sessionKey);
          dispatch({ type: "dataset_reset", key: authOwnerKey });
        }
      }
    }
    void hydrate();

    return () => { requestRef.current += 1; };
  }, [status, ownerKey, workspaceId]);

  useEffect(() => {
    if (!ownerKey || !state.hydrated || state.hydrationKey !== ownerKey) return;
    const datasetKey = `${DATASET_PREFIX}:${ownerKey}`;
    const sessionKey = `${SESSION_PREFIX}:${ownerKey}`;
    if (state.dataset && state.session) {
      window.localStorage.setItem(datasetKey, state.dataset.dataset_id);
      window.localStorage.setItem(sessionKey, state.session.session_id);
    } else {
      window.localStorage.removeItem(datasetKey);
      window.localStorage.removeItem(sessionKey);
    }
  }, [ownerKey, state.dataset, state.session, state.hydrated, state.hydrationKey]);

  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const value = useContext(AppStateContext);
  if (!value) throw new Error("useAppState must be used inside AppStateProvider");
  return value;
}
