"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { ChevronIcon } from "@/components/marketing/chevron-icon";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/#how-it-works", label: "How It Works" },
  { href: "/#technology", label: "Technology" },
  { href: "/pricing", label: "Pricing" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className={cn("sticky top-0 z-50 border-b border-[#141315]/10", open ? "bg-[#f3efe3]" : "bg-[#f3efe3]/88 backdrop-blur-md")}>
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
              className="border-b border-transparent text-xs font-semibold uppercase tracking-[0.18em] text-[#5d5b57] transition-all duration-200 ease-out hover:border-[#141315] hover:text-[#141315]"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <div className="rounded-full border border-[#141315]/10 bg-white/60 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5d5b57]">
            Live enforcement ops
          </div>
          <Link
            href="/auth/login"
            aria-label="Sign in to SniperIP"
            className="rounded-full border border-[#141315]/12 bg-white/70 px-4 py-2 text-sm font-medium text-[#141315] transition-all duration-200 ease-out hover:border-[#141315]"
          >
            Sign In
          </Link>
          <Link
            href="/auth/login"
            aria-label="Start free SniperIP scan"
            className="inline-flex items-center gap-2 rounded-full bg-[#141315] px-4 py-2 text-sm font-semibold text-[#f3efe3] transition-all duration-200 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2"
          >
            Start Free Scan
            <ChevronIcon className="h-3 w-3" />
          </Link>
        </div>

        <button
          type="button"
          aria-label={open ? "Close navigation menu" : "Open navigation menu"}
          onClick={() => setOpen((prev) => !prev)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[#141315]/12 text-[#141315] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2 md:hidden"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open ? (
        <div className="fixed inset-0 z-40 overflow-y-auto bg-[#f3efe3] px-8 pt-24 md:hidden">
          <nav className="flex flex-col gap-6">
            {navLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="text-3xl font-semibold tracking-tight text-[#141315]"
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/auth/login"
              onClick={() => setOpen(false)}
              className="mt-2 text-2xl font-medium text-[#5d5b57]"
            >
              Sign In
            </Link>
            <Link
              href="/auth/login"
              onClick={() => setOpen(false)}
              className="mt-2 inline-flex items-center justify-center gap-2 rounded-full bg-[#141315] px-4 py-3 text-base font-semibold text-[#f3efe3]"
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
