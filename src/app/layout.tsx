import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const headingFont = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-heading",
  weight: ["500", "600", "700", "800"],
});

const bodyFont = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
});

const monoFont = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "SniperIP — Automated IP Protection for D2C Brands",
  description:
    "Discover, verify, and execute DMCA takedowns against counterfeit e-commerce listings. Protect your brand with AI-powered IP enforcement.",
  keywords: ["IP protection", "DMCA takedown", "brand protection", "counterfeit", "D2C"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${headingFont.variable} ${bodyFont.variable} ${monoFont.variable}`}>
      <body className="font-body antialiased bg-background text-foreground">{children}</body>
    </html>
  );
}
