"use client";

import { createContext, useContext, useEffect, useMemo, useReducer } from "react";
import type { AnalysisSession, DatasetSummary } from "./types";
import { createSession, getDataset, getSession } from "./api";

type State = {
  dataset: DatasetSummary | null;
  session: AnalysisSession | null;
  loadingDataset: boolean;
  hydrated: boolean;
};

type Action =
  | { type: "dataset_loaded"; dataset: DatasetSummary; session: AnalysisSession }
  | { type: "dataset_loading" }
  | { type: "session_updated"; session: AnalysisSession }
  | { type: "dataset_reset" };

const initialState: State = { dataset: null, session: null, loadingDataset: false, hydrated: false };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "dataset_loaded":
      return { dataset: action.dataset, session: action.session, loadingDataset: false, hydrated: true };
    case "dataset_loading":
      return { ...state, dataset: null, session: null, loadingDataset: true, hydrated: true };
    case "session_updated":
      return { ...state, session: action.session, hydrated: true };
    case "dataset_reset":
      return { ...initialState, hydrated: true };
    default:
      return state;
  }
}

const DATASET_KEY = "ai-sales-analyst-v4-dataset-id";
const SESSION_KEY = "ai-sales-analyst-v4-session-id";
const AppStateContext = createContext<{ state: State; dispatch: React.Dispatch<Action> } | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    const sessionId = window.localStorage.getItem(SESSION_KEY);
    const datasetId = window.localStorage.getItem(DATASET_KEY);
    if (sessionId) {
      getSession(sessionId).then(async (session) => {
        const dataset = await getDataset(session.dataset_id);
        dispatch({ type: "dataset_loaded", dataset, session });
      }).catch(() => dispatch({ type: "dataset_reset" }));
      return;
    }
    if (!datasetId) {
      dispatch({ type: "dataset_reset" });
      return;
    }
    createSession(datasetId).then(async (session) => {
      const dataset = await getDataset(datasetId);
      dispatch({ type: "dataset_loaded", dataset, session });
    }).catch(() => dispatch({ type: "dataset_reset" }));
  }, []);

  useEffect(() => {
    if (!state.hydrated) return;
    if (state.dataset && state.session) {
      window.localStorage.setItem(DATASET_KEY, state.dataset.dataset_id);
      window.localStorage.setItem(SESSION_KEY, state.session.session_id);
    } else {
      window.localStorage.removeItem(DATASET_KEY);
      window.localStorage.removeItem(SESSION_KEY);
    }
  }, [state.dataset, state.session, state.hydrated]);

  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const value = useContext(AppStateContext);
  if (!value) throw new Error("useAppState must be used inside AppStateProvider");
  return value;
}
