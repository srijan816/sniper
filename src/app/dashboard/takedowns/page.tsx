"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/app/status-badge";
import { listTakedowns, type Takedown } from "@/lib/api";

export default function TakedownsPage() {
  const [rows, setRows] = useState<Takedown[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        setRows(await listTakedowns());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load takedowns.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Takedown Tracking</h1>
        <p className="text-app-base text-muted-foreground">Monitor submission status, case numbers, retries, and resolution outcomes.</p>
      </header>

      {error ? (
        <section className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-app-sm text-destructive">{error}</section>
      ) : null}

      <section className="overflow-x-auto rounded-md border bg-card shadow-sniper-sm">
        <table className="min-w-full">
          <thead className="bg-muted">
            <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3">Platform</th>
              <th className="px-4 py-3">Case Number</th>
              <th className="px-4 py-3">Threat ID</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Submitted</th>
              <th className="px-4 py-3">Retry</th>
            </tr>
          </thead>
          <tbody>
            {!loading && rows.length === 0 ? (
              <tr className="border-t bg-white">
                <td colSpan={6} className="px-4 py-10 text-center text-app-sm text-muted-foreground">
                  No takedown submissions yet.
                </td>
              </tr>
            ) : null}
            {rows.map((row) => (
              <tr key={row.id} className={row.status === "FAILED" ? "border-t bg-red-50/50" : "border-t bg-white"}>
                <td className="px-4 py-3 text-app-sm font-medium">{row.platform}</td>
                <td className="px-4 py-3 font-mono text-app-xs">{row.case_number || "-"}</td>
                <td className="px-4 py-3 font-mono text-app-xs text-muted-foreground">{row.threat_id}</td>
                <td className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    {row.status === "FAILED" ? <AlertTriangle className="h-3.5 w-3.5 text-red-600" /> : null}
                    <StatusBadge status={row.status} />
                  </div>
                </td>
                <td className="px-4 py-3 font-mono text-app-xs text-muted-foreground">
                  {row.submitted_at ? new Date(row.submitted_at).toISOString() : "-"}
                </td>
                <td className="px-4 py-3">
                  {row.retry_count > 0 ? (
                    <span className="rounded-sm bg-amber-100 px-2 py-1 text-app-xs font-medium text-amber-800">
                      Retry {row.retry_count}/5
                    </span>
                  ) : (
                    <span className="text-app-xs text-muted-foreground">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
