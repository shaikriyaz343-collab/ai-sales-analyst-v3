import type { AnalysisSession, DatasetSummary, OverviewResponse, ScopeFilter } from "./types";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export async function onboardDataset(file:File):Promise<{dataset:DatasetSummary;sessionId:string}>{const form=new FormData();form.append("file",file);const response=await fetch(`${API_BASE}/api/v1/onboarding/profile`,{method:"POST",body:form});if(!response.ok){const body=await response.json().catch(()=>({detail:"Upload failed."}));throw new Error(body.detail||"Upload failed.");}const body = await response.json(); if (!body.session_id) throw new Error("The analysis session could not be created."); return { dataset: body.dataset as DatasetSummary, sessionId: body.session_id as string };}

export async function createSession(datasetId:string):Promise<AnalysisSession>{const response=await fetch(`${API_BASE}/api/v1/sessions`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({dataset_id:datasetId}),cache:"no-store"});if(!response.ok){const body=await response.json().catch(()=>({detail:"Could not create analysis session."}));throw new Error(body.detail||"Could not create analysis session.");}return response.json();}
export async function getSession(sessionId:string):Promise<AnalysisSession>{const response=await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`,{cache:"no-store"});if(!response.ok)throw new Error("Analysis session is no longer available.");return response.json();}
export async function updateSessionScope(sessionId:string, filters:ScopeFilter[]):Promise<AnalysisSession>{const response=await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/scope`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filters}),cache:"no-store"});if(!response.ok){const body=await response.json().catch(()=>({detail:"Scope could not be updated."}));throw new Error(body.detail||"Scope could not be updated.");}return response.json();}
export async function getScopeValues(sessionId:string, field:string):Promise<import("./types").ScopeValue[]>{const response=await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/scope-values?field=${encodeURIComponent(field)}`,{cache:"no-store"});if(!response.ok){const body=await response.json().catch(()=>({detail:"Scope values could not be loaded."}));throw new Error(body.detail||"Scope values could not be loaded.");}const body=await response.json();return body.values ?? [];}
export async function resetSessionScope(sessionId:string):Promise<AnalysisSession>{const response=await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/scope/reset`,{method:"POST",cache:"no-store"});if(!response.ok)throw new Error("Scope could not be reset.");return response.json();}

export async function getDataset(datasetId:string):Promise<DatasetSummary>{const response=await fetch(`${API_BASE}/api/v1/datasets/${datasetId}`,{cache:"no-store"});if(!response.ok)throw new Error("Dataset session is no longer available.");return response.json();}
export async function getOverview(datasetId:string, sessionId?:string):Promise<OverviewResponse>{const response=await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/overview${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`,{cache:"no-store"});if(!response.ok){const body=await response.json().catch(()=>({detail:"Overview could not be loaded."}));throw new Error(body.detail||"Overview could not be loaded.");}return response.json();}

export async function getExplore(datasetId: string, metric?: string, dimension?: string, sessionId?: string): Promise<import("./types").ExploreResponse> {
  const params = new URLSearchParams();
  if (metric) params.set("metric", metric);
  if (dimension) params.set("dimension", dimension);
  if (sessionId) params.set("session_id", sessionId);
  const query = params.toString();
  const response = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/explore${query ? `?${query}` : ""}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Explore could not be loaded." }));
    throw new Error(body.detail || "Explore could not be loaded.");
  }
  return response.json();
}


export async function getInsights(datasetId: string, sessionId?: string): Promise<import("./types").InsightsResponse> {
  const response = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/insights${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Insights could not be loaded." }));
    throw new Error(body.detail || "Insights could not be loaded.");
  }
  return response.json();
}


export async function askAnalyst(datasetId: string, question: string, sessionId?: string): Promise<import("./types").AskResponse> {
  const response = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/ask?question=${encodeURIComponent(question)}${sessionId ? `&session_id=${encodeURIComponent(sessionId)}` : ""}`, { cache: "no-store", method: "POST" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "The analyst could not answer that question." }));
    throw new Error(body.detail || "The analyst could not answer that question.");
  }
  return response.json();
}


export async function getActions(datasetId: string, sessionId?: string): Promise<import("./types").ActionsResponse> {
  const response = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/actions${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Actions could not be loaded." }));
    throw new Error(body.detail || "Actions could not be loaded.");
  }
  return response.json();
}


export async function getReport(datasetId: string, sessionId?: string): Promise<import("./types").ReportResponse> {
  const response = await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/report${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Report could not be generated." }));
    throw new Error(body.detail || "Report could not be generated.");
  }
  return response.json();
}


export async function getAlerts(datasetId:string, sessionId:string):Promise<import("./types").AlertsResponse>{const r=await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/alerts?session_id=${encodeURIComponent(sessionId)}`,{cache:"no-store"});if(!r.ok){const b=await r.json().catch(()=>({detail:"Alerts could not be loaded."}));throw new Error(b.detail||"Alerts could not be loaded.");}return r.json();}
export async function createAlert(datasetId:string,sessionId:string,request:{name:string;metric:string;operator:string;threshold:number;cadence:string}):Promise<import("./types").AlertRule>{const r=await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/alerts?session_id=${encodeURIComponent(sessionId)}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(request),cache:"no-store"});if(!r.ok){const b=await r.json().catch(()=>({detail:"Alert could not be created."}));throw new Error(b.detail||"Alert could not be created.");}return r.json();}
export async function deleteAlert(datasetId:string,sessionId:string,ruleId:string){const r=await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/alerts/${ruleId}?session_id=${encodeURIComponent(sessionId)}`,{method:"DELETE",cache:"no-store"});if(!r.ok){const b=await r.json().catch(()=>({detail:"Alert could not be deleted."}));throw new Error(b.detail||"Alert could not be deleted.");}}
export async function evaluateAlerts(datasetId:string,sessionId:string):Promise<import("./types").AlertsResponse>{const r=await fetch(`${API_BASE}/api/v1/datasets/${datasetId}/alerts/evaluate?session_id=${encodeURIComponent(sessionId)}`,{method:"POST",cache:"no-store"});if(!r.ok){const b=await r.json().catch(()=>({detail:"Alerts could not be evaluated."}));throw new Error(b.detail||"Alerts could not be evaluated.");}return r.json();}
