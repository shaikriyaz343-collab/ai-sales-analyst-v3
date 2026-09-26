import type { Metadata } from "next";
import "./globals.css";
import { AppStateProvider } from "../lib/app-state";
import { AuthProvider } from "../lib/auth";

export const metadata: Metadata = {
  title: "Avenlytics | AI Sales Analyst",
  description: "Avenlytics AI Sales Analyst. Upload sales data, understand what changed, and act with evidence — without replacing your CRM.",
  openGraph: {
    title: "Avenlytics | AI Sales Analyst",
    description: "Turn your sales data into an evidence-backed revenue story with Avenlytics, without replacing your CRM.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><AuthProvider><AppStateProvider>{children}</AppStateProvider></AuthProvider></body></html>;
}
