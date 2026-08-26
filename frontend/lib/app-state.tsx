"use client";

import { createContext, useContext, useEffect, useMemo, useReducer, useState } from "react";
import type { DatasetSummary } from "./types";
import { getDataset } from "./api";

type State = {
  dataset: DatasetSummary | null;
  loadingDataset: boolean;
  hydrated: boolean;
};

type Action =
  | { type: "dataset_loaded"; dataset: DatasetSummary }
  | { type: "dataset_reset" }
  | { type: "dataset_loading" };

const initialState: State = { dataset: null, loadingDataset: false, hydrated: false };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "dataset_loaded":
      return { dataset: action.dataset, loadingDataset: false, hydrated: true };
    case "dataset_reset":
      return { ...initialState, hydrated: true };
    case "dataset_loading":
      return { ...state, dataset: null, loadingDataset: true, hydrated: true };
    default:
      return state;
  }
}

const STORAGE_KEY = "ai-sales-analyst-v4-dataset-id";
const AppStateContext = createContext<{ state: State; dispatch: React.Dispatch<Action> } | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    const datasetId = window.localStorage.getItem(STORAGE_KEY);
    if (!datasetId) {
      dispatch({ type: "dataset_reset" });
      return;
    }
    getDataset(datasetId)
      .then((dataset) => dispatch({ type: "dataset_loaded", dataset }))
      .catch(() => dispatch({ type: "dataset_reset" }));
  }, []);

  useEffect(() => {
    if (!state.hydrated) return;
    if (state.dataset) window.localStorage.setItem(STORAGE_KEY, state.dataset.dataset_id);
    else window.localStorage.removeItem(STORAGE_KEY);
  }, [state.dataset, state.hydrated]);

  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const value = useContext(AppStateContext);
  if (!value) throw new Error("useAppState must be used inside AppStateProvider");
  return value;
}
