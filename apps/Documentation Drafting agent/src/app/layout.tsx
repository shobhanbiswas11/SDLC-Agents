import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocuGenius AI — GitHub Documentation Drafter",
  description:
    "AI-powered documentation drafting agent for GitHub repositories. Generate README, API docs, architecture guides and more with a single chat.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
