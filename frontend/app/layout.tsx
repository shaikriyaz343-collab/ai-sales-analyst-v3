import type { Metadata } from "next";
import "./globals.css";
import { AppStateProvider } from "../lib/app-state";
import { AuthProvider } from "../lib/auth";

export const metadata: Metadata = {
  title: "AI Sales Analyst",
  description: "Decision intelligence for sales and revenue teams.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><AuthProvider><AppStateProvider>{children}</AppStateProvider></AuthProvider></body></html>;
}
