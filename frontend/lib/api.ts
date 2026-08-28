import type { DatasetSummary, OverviewResponse } from "./types";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export async function onboardDataset(file:File):Promise<DatasetSummary>{const form=new FormData();form.append("file",file);const response=await fetch(`${API_BASE}/api/v1/onboarding/profile`,{method:"POST",body:form});if(!response.ok){const body=await response.json().catch(()=>({detail:"Upload failed."}));throw new Error(body.detail||"Upload failed.");}return (await response.json()).dataset as DatasetSummary;}
export async function getDataset(datasetId:string):Promise<DatasetSummary>{const response=await fetch(`${API_BASE}/api/v1/datasets/${datasetId}`,{cache:"no-store"});if(!response.ok)throw new Error("Dataset session is no longer available.");return response.json();}
export async function getOverview(datasetId:string):Promise<OverviewResponse>{const response=await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/overview`,{cache:"no-store"});if(!response.ok){const body=await response.json().catch(()=>({detail:"Overview could not be loaded."}));throw new Error(body.detail||"Overview could not be loaded.");}return response.json();}

export async function getExplore(datasetId: string, metric?: string, dimension?: string): Promise<import("./types").ExploreResponse> {
  const params = new URLSearchParams();
  if (metric) params.set("metric", metric);
  if (dimension) params.set("dimension", dimension);
  const query = params.toString();
  const response = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/explore${query ? `?${query}` : ""}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Explore could not be loaded." }));
    throw new Error(body.detail || "Explore could not be loaded.");
  }
  return response.json();
}


export async function getInsights(datasetId: string): Promise<import("./types").InsightsResponse> {
  const response = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/insights`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Insights could not be loaded." }));
    throw new Error(body.detail || "Insights could not be loaded.");
  }
  return response.json();
}


export async function askAnalyst(datasetId: string, question: string): Promise<import("./types").AskResponse> {
  const response = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/ask?question=${encodeURIComponent(question)}`, { cache: "no-store", method: "POST" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "The analyst could not answer that question." }));
    throw new Error(body.detail || "The analyst could not answer that question.");
  }
  return response.json();
}


export async function getActions(datasetId: string): Promise<import("./types").ActionsResponse> {
  const response = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/actions`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Actions could not be loaded." }));
    throw new Error(body.detail || "Actions could not be loaded.");
  }
  return response.json();
}
