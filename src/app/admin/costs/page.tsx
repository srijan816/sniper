"use client";

import { useEffect, useState } from "react";
import { getAdminCosts } from "@/lib/api";

type CostMetrics = {
  serpapi_credits_used: number;
  serpapi_credits_limit: number;
  hf_compute_hours: number;
  zenrows_bandwidth_mb: number;
};

function getTone(percent: number) {
  if (percent >= 100) return "bg-red-500";
  if (percent >= 80) return "bg-amber-500";
  return "bg-sniper-green";
}

export default function AdminCostsPage() {
  const [costs, setCosts] = useState<CostMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminCosts()
      .then(setCosts)
      .catch(() => setError("Failed to load cost metrics"))
      .finally(() => setLoading(false));
  }, []);

  const cards = costs
    ? [
        {
          label: "SerpApi Credits",
          used: costs.serpapi_credits_used,
          limit: costs.serpapi_credits_limit,
          unit: "",
        },
        {
          label: "HuggingFace Compute",
          used: costs.hf_compute_hours,
          limit: 50,
          unit: " hrs",
        },
        {
          label: "ZenRows Bandwidth",
          used: costs.zenrows_bandwidth_mb,
          limit: 2000,
          unit: " MB",
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Cost Monitoring</h1>
        <p className="text-app-base text-muted-foreground">Track infrastructure cost against budget and margin targets.</p>
      </header>

      {error ? <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p> : null}
      {loading ? <p className="text-app-sm text-muted-foreground">Loading…</p> : null}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {cards.map((cost) => {
          const percent = cost.limit > 0 ? Math.min((cost.used / cost.limit) * 100, 100) : 0;
          return (
            <article key={cost.label} className="rounded-md border bg-card p-5 shadow-sniper-sm">
              <h2 className="font-heading text-app-lg font-semibold">{cost.label}</h2>
              <p className="mt-1 font-mono text-app-sm text-muted-foreground">
                {cost.used.toLocaleString()}
                {cost.unit} / {cost.limit.toLocaleString()}
                {cost.unit}
              </p>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
                <div className={`h-full ${getTone(percent)}`} style={{ width: `${percent}%` }} />
              </div>
              <p className="mt-2 text-app-xs text-muted-foreground">{percent.toFixed(1)}% of budget</p>
            </article>
          );
        })}
      </section>
    </div>
  );
}
