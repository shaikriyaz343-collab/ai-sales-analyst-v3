import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { login, signup, logout } from "./api";
import { clearAuth, getToken, setToken } from "./storage";
import type { AuthUser } from "./types";

type AuthState = { loading: boolean; user: AuthUser | null; token: string | null };

const AuthContext = createContext<{
  state: AuthState;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string, organizationName: string) => Promise<void>;
  signOut: () => Promise<void>;
} | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({ loading:true, user:null, token:null });

  useEffect(() => {
    getToken()
      .then((token) => setState({ loading:false, user:null, token }))
      .catch(() => setState({ loading:false, user:null, token:null }));
  }, []);

  async function signIn(email:string,password:string) {
    const result = await login(email.trim(),password);
    await setToken(result.access_token);
    setState({ loading:false, user:result.user, token:result.access_token });
  }

  async function signUp(email:string,password:string,name:string,organizationName:string) {
    const result = await signup(email.trim(),password,name.trim(),organizationName.trim());
    await setToken(result.access_token);
    setState({ loading:false, user:result.user, token:result.access_token });
  }

  async function signOut() {
    try { await logout(); } finally {
      await clearAuth();
      setState({ loading:false, user:null, token:null });
    }
  }

  const value = useMemo(() => ({state,signIn,signUp,signOut}), [state]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const value=useContext(AuthContext);
  if(!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
