"use client";

import Link from "next/link";
import { useMemo, useState, useEffect } from "react";
import { Check, ExternalLink, Search, ShieldCheck, X } from "lucide-react";
import { StatusBadge } from "@/components/app/status-badge";
import { SniperChevron } from "@/components/app/sniper-chevron";
import {
  approveThreat as approveThreatRequest,
  listAssets,
  listThreatAuditLogs,
  listThreats,
  normalizeThreatStatus,
  whitelistThreat as whitelistThreatRequest,
  type Asset,
  type AuditLog,
  type Threat,
} from "@/lib/api";
import { cn, timeAgo } from "@/lib/utils";

type DisplayStatus = "DISCOVERED" | "PENDING_APPROVAL" | "APPROVED" | "SUBMITTED" | "REMOVED" | "FAILED" | "WHITELISTED" | "REJECTED";

const filters: Array<{ key: "ALL" | DisplayStatus; label: string }> = [
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

function similarityPercent(score: number) {
  return score <= 1 ? Math.round(score * 100) : Math.round(score);
}

function threatStatusForDisplay(status: Threat["status"]): DisplayStatus {
  const normalized = normalizeThreatStatus(status);
  if (normalized === "SUBMITTED") return "SUBMITTED";
  if (normalized === "REMOVED") return "REMOVED";
  return normalized as DisplayStatus;
}

function actorTone(actor: string) {
  if (actor === "SYSTEM") return "bg-sniper-green";
  if (actor === "CLIENT_USER") return "bg-sniper-charcoal";
  return "bg-amber-500";
}

export default function ThreatInboxPage() {
  const [threats, setThreats] = useState<Threat[]>([]);
  const [assets, setAssets] = useState<Record<string, Asset>>({});
  const [activeFilter, setActiveFilter] = useState<(typeof filters)[number]["key"]>("ALL");
  const [query, setQuery] = useState("");
  const [selectedThreat, setSelectedThreat] = useState<Threat | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [auditLoading, setAuditLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const [threatList, assetList] = await Promise.all([listThreats(), listAssets()]);
        const assetMap = Object.fromEntries(assetList.map((asset) => [asset.id, asset]));
        setAssets(assetMap);
        setThreats(threatList);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load threats.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const filtered = useMemo(() => {
    return threats.filter((threat) => {
      const displayStatus = threatStatusForDisplay(threat.status);
      const statusMatch = activeFilter === "ALL" || displayStatus === activeFilter;
      const term = query.trim().toLowerCase();
      const assetName = assets[threat.asset_id]?.original_filename || threat.asset_id;
      const queryMatch =
        term.length === 0 ||
        threat.host_domain.toLowerCase().includes(term) ||
        threat.infringing_url.toLowerCase().includes(term) ||
        assetName.toLowerCase().includes(term);
      return statusMatch && queryMatch;
    });
  }, [threats, activeFilter, query, assets]);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    filters.forEach((filter) => {
      if (filter.key === "ALL") {
        map.set(filter.key, threats.length);
        return;
      }
      map.set(filter.key, threats.filter((threat) => threatStatusForDisplay(threat.status) === filter.key).length);
    });
    return map;
  }, [threats]);

  const openThreat = async (threat: Threat) => {
    setSelectedThreat(threat);
    setAuditLoading(true);
    try {
      const logs = await listThreatAuditLogs(threat.id);
      setAuditLogs(logs);
    } catch {
      setAuditLogs([]);
    } finally {
      setAuditLoading(false);
    }
  };

  const approveThreat = async (threatId: string) => {
    try {
      const updated = await approveThreatRequest(threatId);
      setThreats((prev) => prev.map((threat) => (threat.id === threatId ? updated : threat)));
      if (selectedThreat?.id === threatId) {
        setSelectedThreat(updated);
        const logs = await listThreatAuditLogs(threatId);
        setAuditLogs(logs);
      }
    } catch {
      setError("Failed to approve threat. Please retry.");
    }
  };

  const whitelistThreat = async (threatId: string) => {
    try {
      const updated = await whitelistThreatRequest(threatId);
      setThreats((prev) => prev.map((threat) => (threat.id === threatId ? updated : threat)));
      if (selectedThreat?.id === threatId) {
        setSelectedThreat(updated);
        const logs = await listThreatAuditLogs(threatId);
        setAuditLogs(logs);
      }
    } catch {
      setError("Failed to whitelist domain. Please retry.");
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="font-heading text-app-2xl font-bold">Threat Inbox</h1>
          <p className="text-app-base text-muted-foreground">Review detected infringements and submit legally compliant takedowns.</p>
        </div>
      </header>

      {error ? (
        <section className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-app-sm text-destructive">{error}</section>
      ) : null}

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
                  active ? "border-sniper-charcoal bg-sniper-charcoal text-white" : "bg-white text-muted-foreground hover:border-sniper-charcoal/40",
                )}
              >
                {filter.label}
                <span className={cn("rounded-full px-1.5 py-0.5 text-[10px]", active ? "bg-sniper-green text-sniper-charcoal" : "bg-muted text-muted-foreground")}>
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
              {!loading && filtered.length === 0 ? (
                <tr className="border-t bg-white">
                  <td colSpan={6} className="px-4 py-10 text-center text-app-sm text-muted-foreground">
                    No threats available yet.
                  </td>
                </tr>
              ) : null}
              {filtered.map((threat) => {
                const displayStatus = threatStatusForDisplay(threat.status);
                const terminal = displayStatus === "REMOVED" || displayStatus === "WHITELISTED" || displayStatus === "REJECTED";
                const score = similarityPercent(threat.similarity_score);
                const asset = assets[threat.asset_id];
                const originalImage = asset?.thumbnail_url || asset?.storage_url || "/hero-dashboard.webp";
                const infringingImage = threat.infringing_image_url || "/logo-dark.png";
                return (
                  <tr key={threat.id} onClick={() => void openThreat(threat)} className="cursor-pointer border-t bg-white transition hover:bg-sniper-pearl">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <img src={originalImage} alt={asset?.original_filename || threat.asset_id} className="h-12 w-12 rounded-sm border object-cover" />
                        <span className="text-app-xs text-muted-foreground">vs</span>
                        <img src={infringingImage} alt={`Infringing listing from ${threat.host_domain}`} className="h-12 w-12 rounded-sm border object-cover" />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-app-base font-medium text-foreground">{threat.host_domain}</div>
                      <Link
                        href={threat.infringing_url}
                        target="_blank"
                        onClick={(event) => event.stopPropagation()}
                        className="inline-flex max-w-[26rem] items-center gap-1 truncate font-mono text-app-xs text-muted-foreground hover:text-foreground"
                      >
                        {threat.infringing_url}
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <div className={cn("font-mono text-app-sm font-medium", scoreText(score))}>{score}%</div>
                      <div className="mt-1 h-1 w-16 overflow-hidden rounded-full bg-muted">
                        <div className={cn("h-full", scoreColor(score))} style={{ width: `${score}%` }} />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={displayStatus} />
                    </td>
                    <td className="px-4 py-3 text-app-sm text-muted-foreground">{timeAgo(threat.discovered_at)}</td>
                    <td className="px-4 py-3">
                      {terminal ? (
                        <div className="flex justify-end">
                          <StatusBadge status={displayStatus} />
                        </div>
                      ) : (
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void approveThreat(threat.id);
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
                              void whitelistThreat(threat.id);
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
          {filtered.map((threat) => {
            const displayStatus = threatStatusForDisplay(threat.status);
            return (
              <article key={threat.id} className="rounded-md border bg-white p-4 shadow-sniper-sm">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div>
                    <p className="text-app-base font-medium text-foreground">{threat.host_domain}</p>
                    <p className="font-mono text-app-xs text-muted-foreground">{threat.id}</p>
                  </div>
                  <StatusBadge status={displayStatus} />
                </div>
                <button type="button" onClick={() => void openThreat(threat)} className="inline-flex items-center gap-1 text-app-sm font-medium text-foreground underline">
                  View details
                  <ExternalLink className="h-3 w-3" />
                </button>
              </article>
            );
          })}
        </div>

        <div className="flex items-center justify-between border-t px-4 py-3 text-app-xs text-muted-foreground">
          <span>Showing {filtered.length} results</span>
        </div>
      </section>

      {selectedThreat ? (
        <div className="fixed inset-0 z-[70] bg-black/20 backdrop-blur-sm" onClick={() => setSelectedThreat(null)}>
          <aside onClick={(event) => event.stopPropagation()} className="ml-auto h-full w-full max-w-[480px] overflow-y-auto bg-white shadow-sniper-lg animate-slide-in">
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
              <section className="space-y-3 rounded-md border p-4">
                <div className="grid grid-cols-[120px_1fr] gap-2 text-app-sm">
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Status</p>
                  <StatusBadge status={threatStatusForDisplay(selectedThreat.status)} className="w-fit" />
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Threat ID</p>
                  <p className="font-mono">{selectedThreat.id}</p>
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Infringing URL</p>
                  <Link href={selectedThreat.infringing_url} target="_blank" className="font-mono text-app-xs underline">
                    {selectedThreat.infringing_url}
                  </Link>
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Host Domain</p>
                  <p>{selectedThreat.host_domain}</p>
                  <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Discovered At</p>
                  <p className="font-mono text-app-xs">{new Date(selectedThreat.discovered_at).toISOString()}</p>
                </div>
              </section>

              <section>
                <h3 className="font-heading text-app-lg font-semibold">Audit Trail</h3>
                <div className="mt-3 space-y-3 border-l pl-3">
                  {auditLoading ? <p className="text-app-sm text-muted-foreground">Loading audit logs...</p> : null}
                  {!auditLoading && auditLogs.length === 0 ? <p className="text-app-sm text-muted-foreground">No audit events recorded yet.</p> : null}
                  {auditLogs.map((event) => (
                    <div key={event.id} className="relative">
                      <span className={cn("absolute -left-[18px] top-1.5 h-2.5 w-2.5 rounded-full", actorTone(event.changed_by))} />
                      <p className="font-mono text-app-xs text-muted-foreground">{new Date(event.changed_at).toISOString()}</p>
                      <p className="text-app-sm text-foreground">
                        Status changed from {event.old_status ?? "NONE"} to {event.new_status} by {event.changed_by}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <div className="sticky bottom-0 border-t bg-white px-5 py-4">
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => void approveThreat(selectedThreat.id)}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-sniper-green px-3 py-2 font-heading text-app-sm font-bold text-sniper-charcoal"
                >
                  Approve Takedown
                  <SniperChevron className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  onClick={() => void whitelistThreat(selectedThreat.id)}
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
