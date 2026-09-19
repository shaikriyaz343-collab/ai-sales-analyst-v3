"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import MarketingHome from "../components/marketing-home";
import { useAuth } from "../lib/auth";

export default function Home() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard/overview");
  }, [status, router]);

  if (status === "loading") return <main className="marketing-page"><div className="marketing-loading">Preparing your revenue workspace…</div></main>;
  if (status === "authenticated") return null;
  return <MarketingHome />;
}
