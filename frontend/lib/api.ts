import type { AnalysisSession, AuthUser, DatasetSummary, OverviewResponse, ScopeFilter, AuthWorkspace } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ApiOptions = RequestInit & { noStore?: boolean };

async function apiFetch(path: string, options: ApiOptions = {}) {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
    cache: options.cache ?? (options.noStore === false ? undefined : "no-store"),
  });
  return response;
}

async function errorFrom(response: Response, fallback: string) {
  const body = await response.json().catch(() => ({}));
  return new Error(typeof body.detail === "string" ? body.detail : fallback);
}

export async function getCurrentUser(): Promise<AuthUser> {
  const response = await apiFetch("/api/v1/auth/me");
  if (!response.ok) throw new Error("Not authenticated.");
  const body = await response.json();
  return body.user as AuthUser;
}

export async function signup(email: string, password: string, name: string, organizationName: string): Promise<AuthUser> {
  const response = await apiFetch("/api/v1/auth/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password, name, organization_name: organizationName }) });
  if (!response.ok) throw await errorFrom(response, "Could not create your account.");
  const body = await response.json();
  return body.user as AuthUser;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const response = await apiFetch("/api/v1/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
  if (!response.ok) throw await errorFrom(response, "Could not sign in.");
  const body = await response.json();
  return body.user as AuthUser;
}

export async function logout(): Promise<void> {
  const response = await apiFetch("/api/v1/auth/logout", { method: "POST" });
  if (!response.ok) throw await errorFrom(response, "Could not sign out.");
}

export async function getWorkspaces(): Promise<{ organization_id: string; items: AuthWorkspace[] }> {
  const response = await apiFetch("/api/v1/workspaces");
  if (!response.ok) throw await errorFrom(response, "Workspaces could not be loaded.");
  return response.json();
}

export async function createWorkspace(name: string): Promise<AuthWorkspace> {
  const response = await apiFetch("/api/v1/workspaces", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
  if (!response.ok) throw await errorFrom(response, "Workspace could not be created.");
  return response.json();
}

export async function onboardDataset(file: File, workspaceId?: string): Promise<{ dataset: DatasetSummary; sessionId: string }> {
  const form = new FormData();
  form.append("file", file);
  const path = workspaceId ? `/api/v1/onboarding/profile?workspace_id=${encodeURIComponent(workspaceId)}` : "/api/v1/onboarding/profile";
  const response = await apiFetch(path, { method: "POST", body: form });
  if (!response.ok) throw await errorFrom(response, "Upload failed.");
  const body = await response.json();
  if (!body.session_id) throw new Error("The analysis session could not be created.");
  return { dataset: body.dataset as DatasetSummary, sessionId: body.session_id as string };
}

export async function createSession(datasetId: string, workspaceId?: string): Promise<AnalysisSession> {
  const response = await apiFetch("/api/v1/sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ dataset_id: datasetId, ...(workspaceId ? { workspace_id: workspaceId } : {}) }) });
  if (!response.ok) throw await errorFrom(response, "Could not create analysis session.");
  return response.json();
}

export async function getSession(sessionId: string): Promise<AnalysisSession> {
  const response = await apiFetch(`/api/v1/sessions/${sessionId}`);
  if (!response.ok) throw new Error("Analysis session is no longer available.");
  return response.json();
}

export async function updateSessionScope(sessionId: string, filters: ScopeFilter[]): Promise<AnalysisSession> {
  const response = await apiFetch(`/api/v1/sessions/${sessionId}/scope`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filters }) });
  if (!response.ok) throw await errorFrom(response, "Scope could not be updated.");
  return response.json();
}

export async function getScopeValues(sessionId: string, field: string): Promise<import("./types").ScopeValue[]> {
  const response = await apiFetch(`/api/v1/sessions/${sessionId}/scope-values?field=${encodeURIComponent(field)}`);
  if (!response.ok) throw await errorFrom(response, "Scope values could not be loaded.");
  const body = await response.json();
  return body.values ?? [];
}

export async function resetSessionScope(sessionId: string): Promise<AnalysisSession> {
  const response = await apiFetch(`/api/v1/sessions/${sessionId}/scope/reset`, { method: "POST" });
  if (!response.ok) throw await errorFrom(response, "Scope could not be reset.");
  return response.json();
}

export async function getDataset(datasetId: string): Promise<DatasetSummary> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}`);
  if (!response.ok) throw new Error("Dataset is no longer available.");
  return response.json();
}

export async function getOverview(datasetId: string, sessionId?: string): Promise<OverviewResponse> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/overview${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`);
  if (!response.ok) throw await errorFrom(response, "Overview could not be loaded.");
  return response.json();
}

export async function getExplore(datasetId: string, metric?: string, dimension?: string, sessionId?: string): Promise<import("./types").ExploreResponse> {
  const params = new URLSearchParams();
  if (metric) params.set("metric", metric);
  if (dimension) params.set("dimension", dimension);
  if (sessionId) params.set("session_id", sessionId);
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/explore${params.toString() ? `?${params.toString()}` : ""}`);
  if (!response.ok) throw await errorFrom(response, "Explore could not be loaded.");
  return response.json();
}

export async function getForecast(datasetId: string, sessionId?: string): Promise<import("./types").ForecastResponse> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/forecast${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`);
  if (!response.ok) throw await errorFrom(response, "Forecast could not be loaded.");
  return response.json();
}

export async function getInsights(datasetId: string, sessionId?: string): Promise<import("./types").InsightsResponse> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/insights${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`);
  if (!response.ok) throw await errorFrom(response, "Insights could not be loaded.");
  return response.json();
}

export async function askAnalyst(datasetId: string, question: string, sessionId?: string): Promise<import("./types").AskResponse> {
  const params = new URLSearchParams({ question });
  if (sessionId) params.set("session_id", sessionId);
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/ask?${params.toString()}`, { method: "POST" });
  if (!response.ok) throw await errorFrom(response, "The analyst could not answer that question.");
  return response.json();
}

export async function getActions(datasetId: string, sessionId?: string): Promise<import("./types").ActionsResponse> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/actions${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`);
  if (!response.ok) throw await errorFrom(response, "Actions could not be loaded.");
  return response.json();
}

export async function updateActionStatus(datasetId: string, sessionId: string, actionId: string, status: string): Promise<import("./types").ActionItem> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/actions/${encodeURIComponent(actionId)}/status?session_id=${encodeURIComponent(sessionId)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
  if (!response.ok) throw await errorFrom(response, "Action status could not be updated.");
  return response.json();
}

export async function getReport(datasetId: string, sessionId?: string): Promise<import("./types").ReportResponse> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/report${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ""}`);
  if (!response.ok) throw await errorFrom(response, "Report could not be generated.");
  return response.json();
}

export async function getAlerts(datasetId: string, sessionId: string): Promise<import("./types").AlertsResponse> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/alerts?session_id=${encodeURIComponent(sessionId)}`);
  if (!response.ok) throw await errorFrom(response, "Alerts could not be loaded.");
  return response.json();
}

export async function createAlert(datasetId: string, sessionId: string, request: { name: string; metric: string; operator: string; threshold: number; cadence: string }): Promise<import("./types").AlertRule> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/alerts?session_id=${encodeURIComponent(sessionId)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) });
  if (!response.ok) throw await errorFrom(response, "Alert could not be created.");
  return response.json();
}

export async function deleteAlert(datasetId: string, sessionId: string, ruleId: string) {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/alerts/${ruleId}?session_id=${encodeURIComponent(sessionId)}`, { method: "DELETE" });
  if (!response.ok) throw await errorFrom(response, "Alert could not be deleted.");
}

export async function evaluateAlerts(datasetId: string, sessionId: string): Promise<import("./types").AlertsResponse> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/alerts/evaluate?session_id=${encodeURIComponent(sessionId)}`, { method: "POST" });
  if (!response.ok) throw await errorFrom(response, "Alerts could not be evaluated.");
  return response.json();
}

export async function getSavedIntelligence(datasetId: string, sessionId: string): Promise<import("./types").SavedIntelligenceResponse> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/saved?session_id=${encodeURIComponent(sessionId)}`);
  if (!response.ok) throw await errorFrom(response, "Saved intelligence could not be loaded.");
  return response.json();
}

export async function saveIntelligence(datasetId: string, sessionId: string, request: { name: string; source_workspace: string; source_id: string; title?: string; summary?: string; metric?: string; dimension?: string }): Promise<import("./types").SavedIntelligence> {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/saved?session_id=${encodeURIComponent(sessionId)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) });
  if (!response.ok) throw await errorFrom(response, "Intelligence could not be saved.");
  return response.json();
}

export async function deleteSavedIntelligence(datasetId: string, sessionId: string, itemId: string) {
  const response = await apiFetch(`/api/v1/datasets/${datasetId}/saved/${itemId}?session_id=${encodeURIComponent(sessionId)}`, { method: "DELETE" });
  if (!response.ok) throw await errorFrom(response, "Saved intelligence could not be deleted.");
}


export async function getCommercialEntitlements(): Promise<import("./types").CommercialEntitlements> {
  const response = await apiFetch("/api/v1/commercial/entitlements");
  if (!response.ok) throw await errorFrom(response, "Billing information could not be loaded.");
  return response.json();
}

export async function createCommercialCheckout(planId: string): Promise<{ provider: string; provider_session_id: string; checkout_url: string }> {
  const response = await apiFetch("/api/v1/commercial/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan_id: planId }),
  });
  if (!response.ok) throw await errorFrom(response, "Checkout could not be started.");
  return response.json();
}

export async function getCommercialPortal(): Promise<{ portal_url: string }> {
  const response = await apiFetch("/api/v1/commercial/portal");
  if (!response.ok) throw await errorFrom(response, "Customer portal could not be opened.");
  return response.json();
}
