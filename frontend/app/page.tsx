"use client";

import OnboardingScreen from "../components/onboarding-screen";
import AuthScreen from "../components/auth-screen";
import { useAuth } from "../lib/auth";

export default function Home() {
  const { status } = useAuth();
  if (status === "loading") return <main className="auth-page"><div className="auth-shell"><div className="panel auth-loading">Checking your workspace…</div></div></main>;
  return status === "authenticated" ? <OnboardingScreen /> : <AuthScreen />;
}
