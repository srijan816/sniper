"use client";

import { useEffect, useState } from "react";
import { AlertOctagon, DollarSign, Shield, Users } from "lucide-react";
import { ThreatMetric } from "@/components/app/threat-metric";
import { getAdminMetrics } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

type Metrics = {
  total_mrr: number;
  active_clients: number;
  total_threats_discovered: number;
  total_threats_removed: number;
  threats_pending: number;
  dlq_count: number;
};

export default function AdminOverviewPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminMetrics()
      .then(setMetrics)
      .catch(() => setError("Failed to load metrics — are you signed in as an admin?"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Global Metrics</h1>
        <p className="text-app-base text-muted-foreground">Platform-level visibility across revenue, volume, and operational risk.</p>
      </header>

      {error ? <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p> : null}

      {loading ? (
        <p className="text-app-sm text-muted-foreground">Loading…</p>
      ) : metrics ? (
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ThreatMetric
            label="Total MRR"
            value={formatCurrency(metrics.total_mrr)}
            icon={DollarSign}
            positive
          />
          <ThreatMetric
            label="Active Clients"
            value={String(metrics.active_clients)}
            icon={Users}
            positive
          />
          <ThreatMetric
            label="Threats Discovered"
            value={String(metrics.total_threats_discovered)}
            icon={Shield}
            positive
          />
          <ThreatMetric
            label="DLQ Failures"
            value={String(metrics.dlq_count)}
            icon={AlertOctagon}
            positive={metrics.dlq_count === 0}
          />
        </section>
      ) : null}
    </div>
  );
}
