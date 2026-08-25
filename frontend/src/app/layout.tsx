import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DealLab",
  description: "AI deal engineering for enterprise contracts",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
