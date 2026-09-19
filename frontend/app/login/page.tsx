"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import AuthScreen from "../../components/auth-screen";

function LoginContent() {
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode");
  const [initialMode, setInitialMode] = useState<"signin" | "signup">("signin");

  useEffect(() => {
    setInitialMode(mode === "signup" ? "signup" : "signin");
  }, [mode]);

  return <AuthScreen initialMode={initialMode} />;
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="auth-page"><div className="auth-shell"><div className="panel auth-loading">Loading sign in…</div></div></main>}>
      <LoginContent />
    </Suspense>
  );
}
