"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { ChevronIcon } from "@/components/marketing/chevron-icon";
import { Logomark } from "@/components/marketing/logomark";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/#how-it-works", label: "How It Works" },
  { href: "/#technology", label: "Technology" },
  { href: "/pricing", label: "Pricing" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className={cn("sticky top-0 z-50 border-b border-[#E2E8F0]", open ? "bg-white" : "bg-white/80 backdrop-blur-md")}>
      <div className="mx-auto flex h-20 w-full max-w-7xl items-center justify-between px-6">
        <Link href="/" aria-label="SniperIP Home" className="hidden items-center md:flex">
          <Image
            src="/logo-dark.png"
            alt="SniperIP"
            width={280}
            height={280}
            className="h-16 w-auto"
            priority
          />
        </Link>

        <Link
          href="/"
          aria-label="SniperIP Home"
          className="inline-flex items-center text-[#1A1C24] md:hidden"
        >
          <Image
            src="/logo-dark.png"
            alt="SniperIP"
            width={240}
            height={240}
            className="h-10 w-auto"
            priority
          />
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {navLinks.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="border-b border-transparent text-sm font-medium text-[#475569] transition-all duration-200 ease-out hover:border-[#1A1C24] hover:text-[#1A1C24]"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <Link
            href="/auth/login"
            aria-label="Sign in to SniperIP"
            className="rounded-md border border-[#E2E8F0] bg-white px-4 py-2 text-sm font-medium text-[#1A1C24] transition-all duration-200 ease-out hover:border-[#1A1C24]"
          >
            Sign In
          </Link>
          <Link
            href="/auth/login"
            aria-label="Start free SniperIP scan"
            className="inline-flex items-center gap-2 rounded-md bg-[#10D94B] px-4 py-2 text-sm font-semibold text-[#1A1C24] shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)] transition-all duration-200 ease-out hover:scale-105 hover:shadow-[0_10px_15px_-3px_rgba(26,28,36,0.08),0_4px_6px_-2px_rgba(26,28,36,0.04)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2"
          >
            Start Free Scan
            <ChevronIcon className="h-3 w-3" />
          </Link>
        </div>

        <button
          type="button"
          aria-label={open ? "Close navigation menu" : "Open navigation menu"}
          onClick={() => setOpen((prev) => !prev)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-[#E2E8F0] text-[#1A1C24] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2 md:hidden"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open ? (
        <div className="fixed inset-0 z-40 overflow-y-auto bg-white px-8 pt-24 md:hidden">
          <nav className="flex flex-col gap-6">
            {navLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="text-3xl font-semibold tracking-tight text-[#1A1C24]"
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/auth/login"
              onClick={() => setOpen(false)}
              className="mt-2 text-2xl font-medium text-[#475569]"
            >
              Sign In
            </Link>
            <Link
              href="/auth/login"
              onClick={() => setOpen(false)}
              className="mt-2 inline-flex items-center justify-center gap-2 rounded-md bg-[#10D94B] px-4 py-3 text-base font-semibold text-[#1A1C24] shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)]"
            >
              Start Free Scan
              <ChevronIcon className="h-3 w-3" />
            </Link>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
