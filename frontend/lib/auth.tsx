"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { AuthUser, AuthWorkspace } from "./types";
import { createWorkspace, getCurrentUser, login, logout, signup } from "./api";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";
type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  workspaceId: string | null;
  setWorkspaceId: (workspaceId: string) => void;
  refreshUser: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string, organizationName: string) => Promise<void>;
  signOut: () => Promise<void>;
  addWorkspace: (name: string) => Promise<AuthWorkspace>;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const WORKSPACE_KEY = "ai-sales-analyst-v4-workspace-id";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [workspaceId, setWorkspaceIdState] = useState<string | null>(null);

  async function refreshUser() {
    try {
      const next = await getCurrentUser();
      const stored = window.localStorage.getItem(WORKSPACE_KEY);
      const selected = next.workspaces.find((item) => item.id === stored) ?? next.workspaces.find((item) => item.id === next.workspace_id) ?? next.workspaces[0];
      const preferred = selected?.id ?? null;
      setUser(selected ? { ...next, workspace_id: selected.id, workspace_name: selected.name } : next);
      setStatus("authenticated");
      setWorkspaceIdState(preferred);
      if (preferred) window.localStorage.setItem(WORKSPACE_KEY, preferred);
    } catch {
      setUser(null);
      setWorkspaceIdState(null);
      setStatus("unauthenticated");
      window.localStorage.removeItem(WORKSPACE_KEY);
    }
  }

  useEffect(() => {
    void refreshUser();
  }, []);

  function setWorkspaceId(next: string) {
    const selected = user?.workspaces.find((item) => item.id === next);
    if (!selected) return;
    setWorkspaceIdState(next);
    setUser((current) => current ? { ...current, workspace_id: selected.id, workspace_name: selected.name } : current);
    window.localStorage.setItem(WORKSPACE_KEY, next);
  }

  async function signIn(email: string, password: string) {
    const next = await login(email, password);
    setUser(next);
    setStatus("authenticated");
    setWorkspaceIdState(next.workspace_id);
    window.localStorage.setItem(WORKSPACE_KEY, next.workspace_id);
  }

  async function signUp(email: string, password: string, name: string, organizationName: string) {
    const next = await signup(email, password, name, organizationName);
    setUser(next);
    setStatus("authenticated");
    setWorkspaceIdState(next.workspace_id);
    window.localStorage.setItem(WORKSPACE_KEY, next.workspace_id);
  }

  async function signOut() {
    const currentOwner = user && workspaceId ? `${user.id}:${workspaceId}` : null;
    await logout();
    setUser(null);
    setWorkspaceIdState(null);
    setStatus("unauthenticated");
    window.localStorage.removeItem(WORKSPACE_KEY);
    if (currentOwner) {
      window.localStorage.removeItem(`ai-sales-analyst-v4-dataset:${currentOwner}`);
      window.localStorage.removeItem(`ai-sales-analyst-v4-session:${currentOwner}`);
    }
  }

  async function addWorkspace(name: string) {
    const created = await createWorkspace(name);
    const nextUser = await getCurrentUser();
    setUser(nextUser);
    setStatus("authenticated");
    const selected = nextUser.workspaces.find((item) => item.id === created.id) ?? nextUser.workspaces[0];
    setWorkspaceIdState(selected?.id ?? null);
    if (selected) window.localStorage.setItem(WORKSPACE_KEY, selected.id);
    return created;
  }

  const value = useMemo<AuthContextValue>(() => ({ status, user, workspaceId, setWorkspaceId, refreshUser, signIn, signUp, signOut, addWorkspace }), [status, user, workspaceId]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
