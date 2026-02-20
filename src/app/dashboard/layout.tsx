"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  Building2,
  CreditCard,
  FileText,
  ImageIcon,
  LayoutDashboard,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Send,
  ShieldCheck,
  Target,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { listClients } from "@/lib/api";

const operationsItems = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/threats", label: "Threat Inbox", icon: Target },
  { href: "/dashboard/assets", label: "Assets", icon: ImageIcon },
  { href: "/dashboard/takedowns", label: "Takedowns", icon: Send },
  { href: "/dashboard/audit", label: "Audit Log", icon: FileText },
];

const settingsItems = [
  { href: "/dashboard/brand", label: "Brand Profile", icon: Building2 },
  { href: "/dashboard/whitelist", label: "Whitelist", icon: ShieldCheck },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
  { href: "#", label: "Team", icon: Users, soon: true },
];

const crumbLabels: Record<string, string> = {
  dashboard: "Overview",
  threats: "Threat Inbox",
  assets: "Assets",
  takedowns: "Takedowns",
  audit: "Audit Log",
  brand: "Brand Profile",
  whitelist: "Whitelist",
  billing: "Billing",
};

function NavItem({
  href,
  label,
  icon: Icon,
  active,
  collapsed,
  soon,
  onClick,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  collapsed: boolean;
  soon?: boolean;
  onClick?: () => void;
}) {
  const base =
    "group relative flex items-center gap-3 border-l-2 px-3 py-2 text-app-sm transition-all duration-150 ease-out";
  const tone = active
    ? "border-l-sniper-green bg-sniper-charcoal-light text-white"
    : "border-l-transparent text-sniper-ash hover:border-l-sniper-green hover:bg-sniper-charcoal-light hover:text-white";

  if (soon) {
    return (
      <div className={cn(base, "cursor-not-allowed opacity-60", tone)} title={`${label} (Soon)`}>
        <Icon className="h-5 w-5" />
        {!collapsed ? (
          <>
            <span className="truncate">{label}</span>
            <span className="ml-auto rounded-sm bg-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
              Soon
            </span>
          </>
        ) : null}
      </div>
    );
  }

  return (
    <Link href={href} onClick={onClick} className={cn(base, tone)} title={collapsed ? label : undefined}>
      <Icon className={cn("h-5 w-5", active && "text-sniper-green")} />
      {!collapsed ? <span className="truncate">{label}</span> : null}
    </Link>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [companyName, setCompanyName] = useState("Your Brand");
  const [planLabel, setPlanLabel] = useState("No active plan");
  const [usage, setUsage] = useState<number | null>(null);
  const [limit, setLimit] = useState<number | null>(null);

  useEffect(() => {
    const loadClient = async () => {
      try {
        const clients = await listClients();
        if (clients.length === 0) return;
        const client = clients[0];
        setCompanyName(client.company_name || "Your Brand");
        setPlanLabel(`${client.subscription_tier} Tier`);
        setUsage(client.current_month_count ?? null);
        setLimit(client.monthly_threat_limit ?? null);
      } catch {
        // Keep clean fallback values.
      }
    };
    void loadClient();
  }, []);

  const crumbs = useMemo(() => {
    const parts = pathname.split("/").filter(Boolean);
    if (parts.length <= 1) return ["Operations", "Overview"];
    const current = parts[parts.length - 1];
    return ["Operations", crumbLabels[current] ?? "Dashboard"];
  }, [pathname]);

  const usageRatio = usage !== null && limit !== null && limit > 0 ? (usage / limit) * 100 : 0;
  const usageTone =
    usageRatio >= 100
      ? "bg-red-100 text-red-800"
      : usageRatio >= 80
        ? "bg-amber-100 text-amber-800"
        : "bg-sniper-green-muted text-sniper-charcoal";
  const initials = companyName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("") || "AC";

  const sidebar = (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 flex h-screen border-r border-white/10 bg-sniper-charcoal text-white transition-all duration-200",
        collapsed ? "w-sidebar-w-collapsed" : "w-sidebar-w",
      )}
    >
      <div className="flex w-full flex-col">
        <div className="border-b border-white/10 px-4 py-5">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/logo-light.png" alt="SniperIP" width={160} height={160} className={cn("h-9 w-auto", collapsed && "h-8")} />
            {!collapsed ? <span className="sr-only">SniperIP</span> : null}
          </Link>
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-2 py-4">
          <section>
            {!collapsed ? <p className="px-3 pb-2 text-[11px] uppercase tracking-[0.14em] text-sniper-ash">Operations</p> : null}
            <div className="space-y-1">
              {operationsItems.map((item) => (
                <NavItem
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={pathname === item.href}
                  collapsed={collapsed}
                  onClick={() => setMobileOpen(false)}
                />
              ))}
            </div>
          </section>

          <section>
            {!collapsed ? <p className="px-3 pb-2 text-[11px] uppercase tracking-[0.14em] text-sniper-ash">Settings</p> : null}
            <div className="space-y-1">
              {settingsItems.map((item) => (
                <NavItem
                  key={item.label}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={pathname === item.href}
                  collapsed={collapsed}
                  soon={item.soon}
                  onClick={() => setMobileOpen(false)}
                />
              ))}
            </div>
          </section>

          <section>
            {!collapsed ? <p className="px-3 pb-2 text-[11px] uppercase tracking-[0.14em] text-sniper-ash">Founder</p> : null}
            <NavItem
              href="/admin"
              label="Admin Panel"
              icon={Search}
              active={pathname.startsWith("/admin")}
              collapsed={collapsed}
              onClick={() => setMobileOpen(false)}
            />
          </section>
        </nav>

        <div className="border-t border-white/10 p-3">
          <div className="mb-3 flex items-center gap-3 rounded-md bg-white/5 p-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-sniper-green font-mono text-xs font-semibold text-sniper-charcoal">
              {initials}
            </div>
            {!collapsed ? (
              <div className="min-w-0">
                <p className="truncate text-app-sm font-medium text-white">{companyName}</p>
                <p className="text-app-xs text-sniper-ash">{planLabel}</p>
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
            className="hidden w-full items-center justify-center rounded-md border border-white/15 px-2 py-2 text-sniper-ash transition hover:text-white lg:inline-flex"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </aside>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="hidden lg:block">{sidebar}</div>

      {mobileOpen ? (
        <div className="fixed inset-0 z-[60] bg-black/40 lg:hidden" onClick={() => setMobileOpen(false)}>
          <div
            className="h-full w-[16rem] bg-sniper-charcoal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex h-full flex-col text-white">
              <div className="border-b border-white/10 px-4 py-5">
                <Image src="/logo-light.png" alt="SniperIP" width={160} height={160} className="h-9 w-auto" />
              </div>
              <nav className="flex-1 space-y-6 overflow-y-auto px-2 py-4">
                <section>
                  <p className="px-3 pb-2 text-[11px] uppercase tracking-[0.14em] text-sniper-ash">Operations</p>
                  <div className="space-y-1">
                    {operationsItems.map((item) => (
                      <NavItem
                        key={item.href}
                        href={item.href}
                        label={item.label}
                        icon={item.icon}
                        active={pathname === item.href}
                        collapsed={false}
                        onClick={() => setMobileOpen(false)}
                      />
                    ))}
                  </div>
                </section>

                <section>
                  <p className="px-3 pb-2 text-[11px] uppercase tracking-[0.14em] text-sniper-ash">Settings</p>
                  <div className="space-y-1">
                    {settingsItems.map((item) => (
                      <NavItem
                        key={item.label}
                        href={item.href}
                        label={item.label}
                        icon={item.icon}
                        active={pathname === item.href}
                        collapsed={false}
                        soon={item.soon}
                        onClick={() => setMobileOpen(false)}
                      />
                    ))}
                  </div>
                </section>
              </nav>
            </div>
          </div>
        </div>
      ) : null}

      <main className={cn("min-h-screen transition-all lg:ml-sidebar-w", collapsed && "lg:ml-sidebar-w-collapsed")}>
        <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b bg-white px-app-gutter">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border text-muted-foreground hover:text-foreground lg:hidden"
              aria-label="Open navigation"
            >
              <Menu className="h-4 w-4" />
            </button>
            <p className="text-app-sm text-muted-foreground">
              {crumbs[0]} <span className="px-1">&gt;</span>
              <span className="font-medium text-foreground">{crumbs[1]}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className="relative inline-flex h-9 w-9 items-center justify-center rounded-md border text-muted-foreground hover:text-foreground"
              aria-label="Notifications"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-sniper-green" />
            </button>
            {usage !== null && limit !== null && limit > 0 ? (
              <span className={cn("hidden rounded-full px-2.5 py-1 text-app-xs font-medium md:inline-flex", usageTone)}>
                {usage} / {limit} takedowns
              </span>
            ) : (
              <span className="hidden rounded-full bg-sniper-green-muted px-2.5 py-1 text-app-xs font-medium text-sniper-charcoal md:inline-flex">
                Live mode
              </span>
            )}
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-sniper-charcoal text-sm font-semibold text-white"
              aria-label="Account"
            >
              {initials}
            </button>
          </div>
        </header>

        <div className="p-app-gutter">{children}</div>
      </main>
    </div>
  );
}
