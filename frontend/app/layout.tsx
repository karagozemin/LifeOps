import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LifeOps — Paste your document, save your money",
  description:
    "Document to action. Deadline, money_at_risk and .ics in a single call. Agent-consumable, x402-paid.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
