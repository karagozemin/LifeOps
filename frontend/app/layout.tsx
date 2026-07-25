import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LifeOps | Personal Deadline Intelligence",
  description:
    "Turn personal documents into evidence-backed deadlines, money-at-risk insights, action plans, and calendar events.",
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
