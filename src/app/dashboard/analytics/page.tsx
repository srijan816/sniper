"use client";

import { useEffect, useState } from "react";
import { formatCurrency } from "@/lib/utils";
import { getClientAnalytics } from "@/lib/api";

type Analytics = {
  threats_found_this_month: number;
  threats_removed_this_month: number;
  estimated_revenue_protected: number;
  average_order_value: number;
};

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

      {error ? <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p> : null}

      {loading ? (
        <p className="text-app-sm text-muted-foreground">Loading…</p>
      ) : data ? (
        <>
          <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <article className="rounded-md border bg-card p-5 shadow-sniper-sm">
              <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Revenue Protected</p>
              <p className="mt-2 font-heading text-app-3xl font-bold">
                {formatCurrency(data.estimated_revenue_protected)}
              </p>
            </article>
            <article className="rounded-md border bg-card p-5 shadow-sniper-sm">
              <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Threats Found This Month</p>
              <p className="mt-2 font-heading text-app-3xl font-bold">{data.threats_found_this_month}</p>
            </article>
            <article className="rounded-md border bg-card p-5 shadow-sniper-sm">
              <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Threats Removed This Month</p>
              <p className="mt-2 font-heading text-app-3xl font-bold">{data.threats_removed_this_month}</p>
            </article>
          </section>

          <section className="rounded-md border bg-card p-5 shadow-sniper-sm">
            <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Average Order Value</p>
            <p className="mt-2 font-heading text-app-2xl font-bold">{formatCurrency(data.average_order_value)}</p>
            <p className="mt-1 text-app-xs text-muted-foreground">
              Used to estimate revenue protected per takedown confirmed.
            </p>
          </section>
        </>
      ) : null}
    </div>
  );
}
