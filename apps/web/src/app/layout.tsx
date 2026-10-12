import type { Metadata, Viewport } from "next";

import { Providers } from "@/components/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "eBook Studio AI — Write a complete book with an AI team",
    template: "%s · eBook Studio AI",
  },
  description:
    "Turn a topic into a finished, exportable eBook. Eight AI specialists research, plan, write, edit, fact-check, design, publish and market your book.",
  applicationName: "eBook Studio AI",
  keywords: ["ebook", "AI writer", "book generator", "self-publishing", "KDP"],
};

export const viewport: Viewport = {
  themeColor: "#4338ca",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
