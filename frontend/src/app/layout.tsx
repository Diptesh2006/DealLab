import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DealLab | Enterprise Deal Health",
  description: "Stress-test enterprise contract economics before signature.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
