import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "avenlytics.mobile.token";
const WORKSPACE_KEY = "avenlytics.mobile.workspace";
const DATASET_KEY = "avenlytics.mobile.dataset";
const SESSION_KEY = "avenlytics.mobile.session";
const SEEN_ALERTS_KEY = "avenlytics.mobile.seen-alerts";

export const getToken = () => SecureStore.getItemAsync(TOKEN_KEY);
export const setToken = (value: string) => SecureStore.setItemAsync(TOKEN_KEY, value);
export async function clearAuth() {
  await Promise.all([
    SecureStore.deleteItemAsync(TOKEN_KEY),
    SecureStore.deleteItemAsync(WORKSPACE_KEY),
    SecureStore.deleteItemAsync(DATASET_KEY),
    SecureStore.deleteItemAsync(SESSION_KEY),
    SecureStore.deleteItemAsync(SEEN_ALERTS_KEY),
  ]);
}
export const getWorkspaceId = () => SecureStore.getItemAsync(WORKSPACE_KEY);
export const setWorkspaceId = (value: string) => SecureStore.setItemAsync(WORKSPACE_KEY, value);
export const getDatasetId = () => SecureStore.getItemAsync(DATASET_KEY);
export const setDatasetId = (value: string) => SecureStore.setItemAsync(DATASET_KEY, value);
export const getSessionId = () => SecureStore.getItemAsync(SESSION_KEY);
export const setSessionId = (value: string) => SecureStore.setItemAsync(SESSION_KEY, value);
export async function getSeenAlerts(): Promise<string[]> {
  const raw = await SecureStore.getItemAsync(SEEN_ALERTS_KEY);
  if (!raw) return [];
  try { return JSON.parse(raw) as string[]; } catch { return []; }
}
export async function setSeenAlerts(ids: string[]) {
  await SecureStore.setItemAsync(SEEN_ALERTS_KEY, JSON.stringify(ids.slice(-100)));
}
