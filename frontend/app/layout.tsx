import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Unconscious Mind Mapper",
  description: "Map your symbolic inner world through dreams, meditation, and psychedelic experiences.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.variable} style={{ fontFamily: "var(--font-inter, Inter), system-ui, sans-serif" }}>
        <div className="nebula-bg" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
