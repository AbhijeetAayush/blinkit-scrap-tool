import type { Metadata } from "next";
import { DM_Sans, Fraunces } from "next/font/google";
import type { ReactNode } from "react";

import { Nav } from "@/components/nav";

import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const sans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Brand shelf",
  description: "Blinkit digital-shelf intelligence for brand teams",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${sans.variable} font-sans antialiased`}>
        <Nav />
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
