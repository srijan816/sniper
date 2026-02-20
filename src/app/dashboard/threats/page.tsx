"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Check, ExternalLink, Search, ShieldCheck, X } from "lucide-react";
import { StatusBadge } from "@/components/app/status-badge";
import { SniperChevron } from "@/components/app/sniper-chevron";
import { cn, timeAgo } from "@/lib/utils";

type ThreatStatus =
  | "DISCOVERED"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "SUBMITTED"
  | "REMOVED"
  | "FAILED"
  | "WHITELISTED";

type ThreatRecord = {
  id: string;
  assetName: string;
  originalFilename: string;
  hostDomain: string;
  infringingUrl: string;
  similarityScore: number;
  discoveredAt: string;
  status: ThreatStatus;
};

type AuditEvent = {
  id: string;
  timestamp: string;
  actor: "SYSTEM" | "CLIENT" | "ADMIN";
  message: string;
};

const seedThreats: ThreatRecord[] = [
  {
    id: "th_0024",
    assetName: "Hero Sneaker Angle",
    originalFilename: "hero-sneaker-front.jpg",
    hostDomain: "counterfeit-mall.example.com",
    infringingUrl: "https://counterfeit-mall.example.com/premium-sneaker-v2-replica",
    similarityScore: 97,
    discoveredAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    status: "PENDING_APPROVAL",
  },
  {
    id: "th_0025",
    assetName: "Hero Sneaker Angle",
    originalFilename: "hero-sneaker-front.jpg",
    hostDomain: "fakeshop.example.com",
    infringingUrl: "https://fakeshop.example.com/designer-kick-style",
    similarityScore: 94,
    discoveredAt: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    status: "DISCOVERED",
  },
  {
    id: "th_0026",
    assetName: "Bottle Render",
    originalFilename: "matte-bottle-hero.png",
    hostDomain: "wish-deals.example.com",
    infringingUrl: "https://wish-deals.example.com/clone-bottle",
    similarityScore: 98,
    discoveredAt: new Date(Date.now() - 26 * 60 * 60 * 1000).toISOString(),
    status: "REMOVED",
  },
  {
    id: "th_0027",
    assetName: "Bottle Render",
    originalFilename: "matte-bottle-hero.png",
    hostDomain: "promo-factory.example.com",
    infringingUrl: "https://promo-factory.example.com/wholesale-bottle-copy",
    similarityScore: 91,
    discoveredAt: new Date(Date.now() - 7 * 60 * 60 * 1000).toISOString(),
    status: "SUBMITTED",
  },
];

const filters: Array<{ key: "ALL" | ThreatStatus; label: string }> = [
  { key: "ALL", label: "All" },
  { key: "DISCOVERED", label: "Discovered" },
  { key: "PENDING_APPROVAL", label: "Pending" },
  { key: "APPROVED", label: "Approved" },
  { key: "SUBMITTED", label: "Submitted" },
  { key: "REMOVED", label: "Removed" },
  { key: "FAILED", label: "Failed" },
  { key: "WHITELISTED", label: "Whitelisted" },
];

function scoreColor(score: number) {
  if (score >= 95) return "bg-sniper-green";
  if (score >= 90) return "bg-amber-500";
  return "bg-destructive";
}

function scoreText(score: number) {
  if (score >= 95) return "text-[#0A7C2E]";
  if (score >= 90) return "text-amber-700";
  return "text-red-700";
}

function makeAudit(threat: ThreatRecord): AuditEvent[] {
  return [
    {
      id: `${threat.id}-1`,
      timestamp: new Date(new Date(threat.discoveredAt).getTime() + 4 * 60 * 1000).toISOString(),
      actor: "SYSTEM",
      message: "Status changed from NONE to DISCOVERED by SYSTEM",
    },
    {
      id: `${threat.id}-2`,
      timestamp: new Date(new Date(threat.discoveredAt).getTime() + 25 * 60 * 1000).toISOString(),
      actor: "CLIENT",
      message: "Status changed from DISCOVERED to PENDING_APPROVAL by CLIENT",
    },
    {
      id: `${threat.id}-3`,
      timestamp: new Date(new Date(threat.discoveredAt).getTime() + 35 * 60 * 1000).toISOString(),
      actor: "SYSTEM",
      message: "Status changed from PENDING_APPROVAL to SUBMITTED by SYSTEM",
    },
  ];
}

export default function ThreatInboxPage() {
  const [threats, setThreats] = useState(seedThreats);
  const [activeFilter, setActiveFilter] = useState<(typeof filters)[number]["key"]>("ALL");
  const [query, setQuery] = useState("");
  const [selectedThreat, setSelectedThreat] = useState<ThreatRecord | null>(null);

  const filtered = useMemo(() => {
    return threats.filter((threat) => {
      const statusMatch = activeFilter === "ALL" || threat.status === activeFilter;
      const term = query.trim().toLowerCase();
      const queryMatch =
        term.length === 0 ||
        threat.hostDomain.toLowerCase().includes(term) ||
        threat.infringingUrl.toLowerCase().includes(term) ||
        threat.assetName.toLowerCase().includes(term);

      return statusMatch && queryMatch;
    });
  }, [threats, activeFilter, query]);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    filters.forEach((filter) => {
      if (filter.key === "ALL") {
        map.set(filter.key, threats.length);
        return;
      }

      map.set(filter.key, threats.filter((threat) => threat.status === filter.key).length);
    });
    return map;
  }, [threats]);

  const approveThreat = (threatId: string) => {
    setThreats((prev) =>
      prev.map((threat) => (threat.id === threatId ? { ...threat, status: "APPROVED" } : threat)),
    );
  };

  const whitelistThreat = (threatId: string) => {
    setThreats((prev) =>
      prev.map((threat) => (threat.id === threatId ? { ...threat, status: "WHITELISTED" } : threat)),
    );
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="font-heading text-app-2xl font-bold">Threat Inbox</h1>
          <p className="text-app-base text-muted-foreground">
            Review detected infringements and submit legally compliant takedowns.
          </p>
        </div>
        <button
          type="button"
          className="inline-flex w-fit items-center gap-2 rounded-md border bg-white px-3 py-2 text-app-sm text-foreground transition hover:bg-muted"
        >
          <ShieldCheck className="h-4 w-4" />
          Export CSV
        </button>
      </header>

      <section className="space-y-4 rounded-md border bg-card p-4 shadow-sniper-sm">
        <div className="flex flex-wrap gap-2">
          {filters.map((filter) => {
            const active = activeFilter === filter.key;
            const count = counts.get(filter.key) ?? 0;

            return (
              <button
                key={filter.key}
                type="button"
                onClick={() => setActiveFilter(filter.key)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-app-xs font-medium transition",
                  active
                    ? "border-sniper-charcoal bg-sniper-charcoal text-white"
                    : "bg-white text-muted-foreground hover:border-sniper-charcoal/40",
                )}
              >
                {filter.label}
                <span
                  className={cn(
                    "rounded-full px-1.5 py-0.5 text-[10px]",
                    active ? "bg-sniper-green text-sniper-charcoal" : "bg-muted text-muted-foreground",
                  )}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <label className="relative block">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by URL, domain, or asset name..."
            className="h-10 w-full rounded-md border bg-white pl-9 pr-3 text-app-sm outline-none transition focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
          />
        </label>
      </section>

      <section className="rounded-md border bg-card shadow-sniper-sm">
        <div className="hidden overflow-x-auto lg:block">
          <table className="min-w-full">
            <thead className="bg-muted">
              <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-3">Comparison</th>
                <th className="px-4 py-3">Domain</th>
                <th className="px-4 py-3">Similarity</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Discovered</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((threat) => {
                const terminal = threat.status === "REMOVED" || threat.status === "WHITELISTED";
                return (
                  <tr
                    key={threat.id}
                    onClick={() => setSelectedThreat(threat)}
                    className="cursor-pointer border-t bg-white transition hover:bg-sniper-pearl"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Image
                          src="/hero-dashboard.webp"
                          alt={threat.originalFilename}
                          width={48}
                          height={48}
                          className="h-12 w-12 rounded-sm border object-cover"
                        />
                        <span className="text-app-xs text-muted-foreground">vs</span>
                        <Image
                          src="/threat-inbox-demo.webp"
                          alt={`Infringing listing from ${threat.hostDomain}`}
                          width={48}
                          height={48}
                          className="h-12 w-12 rounded-sm border object-cover"
                        />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-app-base font-medium text-foreground">{threat.hostDomain}</div>
                      <Link
                        href={threat.infringingUrl}
                        target="_blank"
                        onClick={(event) => event.stopPropagation()}
                        className="inline-flex max-w-[26rem] items-center gap-1 truncate font-mono text-app-xs text-muted-foreground hover:text-foreground"
                      >
                        {threat.infringingUrl}
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <div className={cn("font-mono text-app-sm font-medium", scoreText(threat.similarityScore))}>
                        {threat.similarityScore}%
                      </div>
                      <div className="mt-1 h-1 w-16 overflow-hidden rounded-full bg-muted">
                        <div className={cn("h-full", scoreColor(threat.similarityScore))} style={{ width: `${threat.similarityScore}%` }} />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={threat.status} />
                    </td>
                    <td className="px-4 py-3 text-app-sm text-muted-foreground">{timeAgo(threat.discoveredAt)}</td>
                    <td className="px-4 py-3">
                      {terminal ? (
                        <div className="flex justify-end">
                          <StatusBadge status={threat.status} />
                        </div>
                      ) : (
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              approveThreat(threat.id);
                            }}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-sm bg-sniper-green text-sniper-charcoal transition hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-sniper-green"
                            aria-label="Approve takedown"
                          >
                            <Check className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              whitelistThreat(threat.id);
                            }}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-sm border bg-muted text-muted-foreground transition hover:bg-secondary"
                            aria-label="Whitelist domain"
                          >
                            <ShieldCheck className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="space-y-3 p-4 lg:hidden">
          {filtered.map((threat) => (
            <article key={threat.id} className="rounded-md border bg-white p-4 shadow-sniper-sm">
              <div className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <p className="text-app-base font-medium text-foreground">{threat.hostDomain}</p>
                  <p className="font-mono text-app-xs text-muted-foreground">{threat.id}</p>
                </div>
                <StatusBadge status={threat.status} />
              </div>
              <div className="mb-3 flex items-center gap-2">
                <Image
                  src="/hero-dashboard.webp"
                  alt={threat.originalFilename}
                  width={56}
                  height={56}
                  className="h-14 w-14 rounded-sm border object-cover"
                />
                <Image
                  src="/threat-inbox-demo.webp"
                  alt={`Infringing listing from ${threat.hostDomain}`}
                  width={56}
                  height={56}
                  className="h-14 w-14 rounded-sm border object-cover"
                />
              </div>
              <button
                type="button"
                onClick={() => setSelectedThreat(threat)}
                className="inline-flex items-center gap-1 text-app-sm font-medium text-foreground underline"
              >
                View details
                <ExternalLink className="h-3 w-3" />
              </button>
            </article>
          ))}
        </div>

        <div className="flex items-center justify-between border-t px-4 py-3 text-app-xs text-muted-foreground">
          <span>Showing {filtered.length} results</span>
          <div className="flex gap-2">
            <button type="button" className="rounded-sm border px-2 py-1 hover:bg-muted">
              Prev
            </button>
            <button type="button" className="rounded-sm border px-2 py-1 hover:bg-muted">
              Next
            </button>
          </div>
        </div>
      </section>

      {selectedThreat ? (
        <div className="fixed inset-0 z-[70] bg-black/20 backdrop-blur-sm" onClick={() => setSelectedThreat(null)}>
          <aside
            onClick={(event) => event.stopPropagation()}
            className="ml-auto h-full w-full max-w-[480px] overflow-y-auto bg-white shadow-sniper-lg animate-slide-in"
          >
            <div className="sticky top-0 flex items-center justify-between border-b bg-white px-5 py-4">
              <h2 className="font-heading text-app-xl font-semibold">Threat detail</h2>
              <button
                type="button"
                onClick={() => setSelectedThreat(null)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-sm border text-muted-foreground hover:text-foreground"
                aria-label="Close threat panel"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-6 p-5">
              <section className="grid grid-cols-2 gap-3">
                <div>
                  <Image
                    src="/hero-dashboard.webp"
                    alt={selectedThreat.originalFilename}
                    width={220}
                    height={160}
                    className="h-36 w-full rounded-sm border object-cover"
                  />
                  <p className="mt-1 text-app-xs font-medium text-[#0A7C2E]">Your Asset</p>
                </div>
                <div>
                  <Image
                    src="/threat-inbox-demo.webp"
                    alt={`Infringing listing from ${selectedThreat.hostDomain}`}
                    width={220}
                    height={160}
                    className="h-36 w-full rounded-sm border object-cover"
                  />
                  <p className="mt-1 text-app-xs font-medium text-destructive">Infringing Listing</p>
                </div>
              </section>

              <section className="space-y-3 rounded-md border p-4">
                <div className="grid grid-cols-[120px_1fr] gap-2 text-app-sm">
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Status</p>
                  <StatusBadge status={selectedThreat.status} className="w-fit" />
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Threat ID</p>
                  <p className="font-mono">{selectedThreat.id}</p>
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Infringing URL</p>
                  <Link href={selectedThreat.infringingUrl} target="_blank" className="font-mono text-app-xs underline">
                    {selectedThreat.infringingUrl}
                  </Link>
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Host Domain</p>
                  <p>{selectedThreat.hostDomain}</p>
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Discovered At</p>
                  <p className="font-mono text-app-xs">{new Date(selectedThreat.discoveredAt).toISOString()}</p>
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Asset</p>
                  <p>{selectedThreat.assetName}</p>
                </div>
              </section>

              <section>
                <h3 className="font-heading text-app-lg font-semibold">Audit Trail</h3>
                <div className="mt-3 space-y-3 border-l pl-3">
                  {makeAudit(selectedThreat).map((event) => (
                    <div key={event.id} className="relative">
                      <span
                        className={cn(
                          "absolute -left-[18px] top-1.5 h-2.5 w-2.5 rounded-full",
                          event.actor === "SYSTEM"
                            ? "bg-sniper-green"
                            : event.actor === "CLIENT"
                              ? "bg-sniper-charcoal"
                              : "bg-amber-500",
                        )}
                      />
                      <p className="font-mono text-app-xs text-muted-foreground">
                        {new Date(event.timestamp).toISOString()}
                      </p>
                      <p className="text-app-sm text-foreground">{event.message}</p>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <div className="sticky bottom-0 border-t bg-white px-5 py-4">
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => approveThreat(selectedThreat.id)}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-sniper-green px-3 py-2 font-heading text-app-sm font-bold text-sniper-charcoal"
                >
                  Approve Takedown
                  <SniperChevron className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  onClick={() => whitelistThreat(selectedThreat.id)}
                  className="rounded-md border px-3 py-2 text-app-sm text-muted-foreground"
                >
                  Whitelist Domain
                </button>
              </div>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
