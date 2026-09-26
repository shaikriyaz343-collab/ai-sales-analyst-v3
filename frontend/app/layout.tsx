import type { Metadata } from "next";
import "./globals.css";
import { AppStateProvider } from "../lib/app-state";
import { AuthProvider } from "../lib/auth";

export const metadata: Metadata = {
  title: "Avelyntics | AI Sales Analyst",
  description: "Avelyntics AI Sales Analyst: upload sales data, understand what changed, and act on validated evidence without replacing your CRM.",
  openGraph: {
    title: "Avelyntics | AI Sales Analyst",
    description: "Avelyntics turns sales data into an evidence-backed revenue story without replacing your CRM.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><AuthProvider><AppStateProvider>{children}</AppStateProvider></AuthProvider></body></html>;
}
