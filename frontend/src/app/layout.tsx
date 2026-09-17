import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CubeSat Digital Twin — Mission Control",
  description: "2U CubeSat wildfire smoke detection digital twin",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-mission-dark text-slate-200 min-h-screen">{children}</body>
    </html>
  );
}
