"use client";

import { useEffect, useState } from "react";
import { formatCurrency } from "@/lib/utils";
import { getClientAnalytics } from "@/lib/api";

type Analytics = {
  threats_found_this_month: number;
  threats_removed_this_month: number;
  estimated_revenue_protected: number;
  average_order_value: number;
  threats_discovered_total: number;
  takedowns_completed_total: number;
  takedowns_completed_this_month: number;
  average_time_to_takedown_hours: number | null;
  bad_actors_identified: number;
  platforms_breakdown: Record<string, number>;
  monthly_trend: Array<{ month: string; threats: number; takedowns: number }>;
};

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <article className="rounded-md border bg-card p-5 shadow-sniper-sm">
      <p className="text-app-xs uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-2 font-heading text-app-3xl font-bold">{value}</p>
    </article>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getClientAnalytics()
      .then(setData)
      .catch(() => setError("Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Analytics</h1>
        <p className="text-app-base text-muted-foreground">
          Performance summary for discovery and enforcement.
        </p>
      </header>

      {error ? (
        <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p>
      ) : null}

      {loading ? (
        <p className="text-app-sm text-muted-foreground">Loading…</p>
      ) : data ? (
        <>
          {/* Primary KPIs */}
          <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <StatCard label="Revenue Protected" value={formatCurrency(data.estimated_revenue_protected)} />
            <StatCard label="Threats This Month" value={data.threats_found_this_month} />
            <StatCard label="Removed This Month" value={data.threats_removed_this_month} />
          </section>

          {/* Secondary KPIs */}
          <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Total Threats Found" value={data.threats_discovered_total} />
            <StatCard label="Total Takedowns" value={data.takedowns_completed_total} />
            <StatCard label="Bad Actors" value={data.bad_actors_identified} />
            <StatCard
              label="Avg Time to Takedown"
              value={data.average_time_to_takedown_hours != null ? `${data.average_time_to_takedown_hours.toFixed(1)}h` : "—"}
            />
          </section>

          {/* Platforms breakdown */}
          {Object.keys(data.platforms_breakdown).length > 0 && (
            <section className="rounded-md border bg-card p-5 shadow-sniper-sm space-y-3">
              <p className="text-app-sm font-semibold">Threats by Platform</p>
              <div className="space-y-2">
                {Object.entries(data.platforms_breakdown)
                  .sort(([, a], [, b]) => b - a)
                  .map(([platform, count]) => {
                    const total = Object.values(data.platforms_breakdown).reduce((s, v) => s + v, 0);
                    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                    return (
                      <div key={platform} className="flex items-center gap-3">
                        <span className="w-24 text-app-xs capitalize text-muted-foreground">{platform}</span>
                        <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-sniper-green"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="w-8 text-right text-app-xs font-medium">{count}</span>
                      </div>
                    );
                  })}
              </div>
            </section>
          )}

          {/* Monthly trend table */}
          {data.monthly_trend.length > 0 && (
            <section className="rounded-md border bg-card p-5 shadow-sniper-sm space-y-3">
              <p className="text-app-sm font-semibold">Monthly Trend</p>
              <div className="overflow-x-auto">
                <table className="w-full text-app-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-2 font-medium">Month</th>
                      <th className="pb-2 font-medium">Threats Found</th>
                      <th className="pb-2 font-medium">Takedowns</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.monthly_trend.map((row) => (
                      <tr key={row.month}>
                        <td className="py-2 font-mono text-app-xs">{row.month}</td>
                        <td className="py-2">{row.threats}</td>
                        <td className="py-2">{row.takedowns}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* AOV note */}
          <section className="rounded-md border bg-card p-5 shadow-sniper-sm">
            <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Average Order Value</p>
            <p className="mt-2 font-heading text-app-2xl font-bold">{formatCurrency(data.average_order_value)}</p>
            <p className="mt-1 text-app-xs text-muted-foreground">
              Used to estimate revenue protected per confirmed takedown.
            </p>
          </section>
        </>
      ) : null}
    </div>
  );
}
