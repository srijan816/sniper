"use client";

import Link from "next/link";
import { AlertTriangle, Clock3, ShieldCheck, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ThreatMetric } from "@/components/app/threat-metric";
import { StatusBadge } from "@/components/app/status-badge";
import { listThreats, normalizeThreatStatus, type Threat } from "@/lib/api";
import { timeAgo } from "@/lib/utils";

function similarityPercent(score: number) {
  return score <= 1 ? Math.round(score * 100) : Math.round(score);
}

export default function DashboardOverviewPage() {
  const [threats, setThreats] = useState<Threat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        setThreats(await listThreats());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard data.");
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  const stats = useMemo(() => {
    const discovered = threats.length;
    const removed = threats.filter((t) => normalizeThreatStatus(t.status) === "REMOVED").length;
    const pending = threats.filter((t) => {
      const status = normalizeThreatStatus(t.status);
      return status === "DISCOVERED" || status === "PENDING_APPROVAL" || status === "APPROVED" || status === "SUBMITTED";
    }).length;
    const aov = Number(process.env.NEXT_PUBLIC_AVERAGE_ORDER_VALUE || 120);
    const revenue = removed * (Number.isFinite(aov) ? aov : 120);
    return { discovered, removed, pending, revenue };
  }, [threats]);

  const recentThreats = useMemo(
    () =>
      [...threats]
        .sort((a, b) => new Date(b.discovered_at).getTime() - new Date(a.discovered_at).getTime())
        .slice(0, 6),
    [threats],
  );

  return (
    <div className="space-y-app-section">
      <section className="rounded-md border bg-card p-6 shadow-sniper-md">
        <p className="text-app-sm text-muted-foreground">Current data</p>
        <h1 className="mt-1 font-heading text-app-2xl font-bold text-foreground">
          {loading ? "Loading dashboard metrics..." : `${stats.discovered} threats found -> $${stats.revenue.toLocaleString()} estimated revenue protected`}
        </h1>
        <p className="mt-2 text-app-base text-muted-foreground">
          {error
            ? "Live data failed to load. Check backend connectivity."
            : "Metrics are calculated from your real threat pipeline."}
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ThreatMetric label="Threats Discovered" value={loading ? "--" : String(stats.discovered)} icon={AlertTriangle} positive />
        <ThreatMetric label="Threats Removed" value={loading ? "--" : String(stats.removed)} icon={ShieldCheck} positive />
        <ThreatMetric label="Revenue Protected" value={loading ? "--" : `$${stats.revenue.toLocaleString()}`} icon={TrendingUp} positive />
        <ThreatMetric label="Pending Review" value={loading ? "--" : String(stats.pending)} icon={Clock3} />
      </section>

      <section className="rounded-md border bg-card shadow-sniper-sm">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="font-heading text-app-xl font-semibold">Recent threats</h2>
          <Link href="/dashboard/threats" className="text-app-sm font-medium text-foreground underline-offset-2 hover:underline">
            Open inbox
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-muted">
              <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
                <th className="px-5 py-3">Domain</th>
                <th className="px-5 py-3">URL</th>
                <th className="px-5 py-3">Similarity</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Discovered</th>
              </tr>
            </thead>
            <tbody>
              {!loading && recentThreats.length === 0 ? (
                <tr className="border-t bg-white">
                  <td colSpan={5} className="px-5 py-8 text-center text-app-sm text-muted-foreground">
                    No threats yet. Upload assets to start monitoring.
                  </td>
                </tr>
              ) : null}
              {recentThreats.map((threat) => (
                <tr key={threat.id} className="border-t bg-white transition hover:bg-muted/60">
                  <td className="px-5 py-3 text-app-base font-medium text-foreground">{threat.host_domain}</td>
                  <td className="px-5 py-3 font-mono text-app-xs text-muted-foreground">{threat.infringing_url}</td>
                  <td className="px-5 py-3 font-mono text-app-sm text-foreground">{similarityPercent(threat.similarity_score)}%</td>
                  <td className="px-5 py-3">
                    <StatusBadge status={normalizeThreatStatus(threat.status)} />
                  </td>
                  <td className="px-5 py-3 text-app-sm text-muted-foreground">{timeAgo(threat.discovered_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
