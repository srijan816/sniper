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
  title: "SniperIP — Site Under Construction",
  description: "SniperIP is currently under construction. Check back soon.",
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${headingFont.variable} ${bodyFont.variable} ${monoFont.variable} bg-[#05070a]`}
    >
      <head>
        {/* Preload the text-free still so first paint matches the final look */}
        <link rel="preload" as="image" href="/under-construction/bg-still.jpg" />
        <link rel="preload" as="video" href="/under-construction/bg.mp4" type="video/mp4" />
      </head>
      <body className="font-body antialiased bg-[#05070a] text-white">{children}</body>
    </html>
  );
}
