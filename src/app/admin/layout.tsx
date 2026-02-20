"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AlertOctagon, ArrowLeft, BarChart2, DollarSign } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/admin", label: "Overview", icon: BarChart2 },
  { href: "/admin/costs", label: "Cost Monitoring", icon: DollarSign },
  { href: "/admin/dlq", label: "Dead Letter Queue", icon: AlertOctagon },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="dark min-h-screen bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-sidebar-w border-r border-white/10 bg-sniper-charcoal lg:block">
        <div className="border-b border-white/10 px-5 py-5">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/logo-light.png" alt="SniperIP" width={160} height={160} className="h-9 w-auto" />
          </Link>
          <p className="mt-2 text-app-xs uppercase tracking-[0.14em] text-red-300">Founder Admin</p>
        </div>

        <nav className="space-y-1 px-3 py-4">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 border-l-2 px-3 py-2 text-app-sm transition",
                  active
                    ? "border-l-sniper-green bg-white/5 text-white"
                    : "border-l-transparent text-sniper-ash hover:border-l-sniper-green hover:bg-white/5 hover:text-white",
                )}
              >
                <Icon className={cn("h-4 w-4", active && "text-sniper-green")} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-0 w-full border-t border-white/10 p-3">
          <Link
            href="/dashboard"
            className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-white/15 px-3 py-2 text-app-sm text-sniper-ash hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Client App
          </Link>
        </div>
      </aside>

      <main className="lg:ml-sidebar-w">
        <header className="sticky top-0 z-30 border-b border-white/10 bg-background/95 px-app-gutter py-3 backdrop-blur">
          <h1 className="font-heading text-app-lg font-semibold">Founder Operations</h1>
        </header>
        <div className="p-app-gutter">{children}</div>
      </main>
    </div>
  );
}
