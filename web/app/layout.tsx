import type { Metadata, Viewport } from "next";
import "./globals.css";
import { OneSignalInit } from "@/components/OneSignalInit";

export const metadata: Metadata = {
  title: "Morning Digest",
  description: "Your personal morning briefing — markets, politics, AI, sport.",
  appleWebApp: {
    capable: true,
    title: "Morning Digest",
    statusBarStyle: "black-translucent",
  },
};

export const viewport: Viewport = {
  themeColor: "#0d1117",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body>
        <OneSignalInit />
        {children}
      </body>
    </html>
  );
}
