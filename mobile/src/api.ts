import Constants from "expo-constants";
import type {
  ActionsResponse, AlertsResponse, AskResponse, AuthUser, CommercialEntitlements,
  InsightsResponse, MobileContext, Overview, ReportResponse, SavedResponse, AnalysisSession
} from "./types";
import { getToken } from "./storage";

const extra = Constants.expoConfig?.extra as { apiBaseUrl?: string } | undefined;
const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  extra?.apiBaseUrl ||
  "https://ai-sales-analyst-v3-production.up.railway.app"
).replace(/\/$/, "");

async function request<T>(path: string, options: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && typeof options.body === "string") headers.set("Content-Type", "application/json");
  if (auth) {
    const token = await getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Avenlytics could not complete that request.");
  }
  return response.json();
}

export function login(email: string, password: string) {
  return request<{ user: AuthUser; access_token: string }>("/api/v1/mobile/auth/login", {
    method: "POST", body: JSON.stringify({ email, password }),
  }, false);
}
export function signup(email: string, password: string, name: string, organizationName: string) {
  return request<{ user: AuthUser; access_token: string }>("/api/v1/mobile/auth/signup", {
    method: "POST", body: JSON.stringify({ email, password, name, organization_name: organizationName }),
  }, false);
}
export function logout() { return request<{status:string}>("/api/v1/mobile/auth/logout", {method:"POST"}); }
export function getContext() { return request<MobileContext>("/api/v1/mobile/context"); }
export function createSession(datasetId: string, workspaceId: string) {
  return request<AnalysisSession>("/api/v1/sessions", { method:"POST", body: JSON.stringify({ dataset_id: datasetId, workspace_id: workspaceId }) });
}
export function getOverview(datasetId: string, sessionId: string) {
  return request<Overview>(`/api/v1/datasets/${datasetId}/overview?session_id=${encodeURIComponent(sessionId)}`);
}
export function getActions(datasetId: string, sessionId: string) {
  return request<ActionsResponse>(`/api/v1/datasets/${datasetId}/actions?session_id=${encodeURIComponent(sessionId)}`);
}
export function getInsights(datasetId: string, sessionId: string) {
  return request<InsightsResponse>(`/api/v1/datasets/${datasetId}/insights?session_id=${encodeURIComponent(sessionId)}`);
}
export function askAnalyst(datasetId: string, question: string, sessionId: string) {
  const params = new URLSearchParams({ question, session_id: sessionId });
  return request<AskResponse>(`/api/v1/datasets/${datasetId}/ask?${params.toString()}`, { method:"POST" });
}
export function getReport(datasetId: string, sessionId: string) {
  return request<ReportResponse>(`/api/v1/datasets/${datasetId}/report?session_id=${encodeURIComponent(sessionId)}`);
}
export function getAlerts(datasetId: string, sessionId: string) {
  return request<AlertsResponse>(`/api/v1/datasets/${datasetId}/alerts?session_id=${encodeURIComponent(sessionId)}`);
}
export function evaluateAlerts(datasetId: string, sessionId: string) {
  return request<AlertsResponse>(`/api/v1/datasets/${datasetId}/alerts/evaluate?session_id=${encodeURIComponent(sessionId)}`, { method:"POST" });
}
export function getSaved(datasetId: string, sessionId: string) {
  return request<SavedResponse>(`/api/v1/datasets/${datasetId}/saved?session_id=${encodeURIComponent(sessionId)}`);
}
export function getEntitlements() { return request<CommercialEntitlements>("/api/v1/commercial/entitlements"); }
export function registerPushToken(token: string, platform: string) {
  return request<{status:string}>("/api/v1/mobile/push-token", {method:"POST", body: JSON.stringify({token, platform})});
}
