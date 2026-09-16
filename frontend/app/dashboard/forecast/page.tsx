"use client";

import ForecastView from "../../../components/forecast-view";
import { useAppState } from "../../../lib/app-state";

export default function ForecastPage() {
  const { state } = useAppState();

  if (!state.dataset) {
    return <div className="empty-state"><span className="empty-icon">↗</span><h1>Upload your business data</h1><p>Start with a validated sales-pipeline CSV or Excel file to build a forecast.</p></div>;
  }

  return <ForecastView datasetId={state.dataset.dataset_id} sessionId={state.session?.session_id} />;
}
