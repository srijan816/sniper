"use client";

import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/app/status-badge";
import { listAuditLogs, normalizeThreatStatus, type AuditLog } from "@/lib/api";

function actorBadgeClass(actor: string) {
  if (actor === "SYSTEM") return "border-sniper-charcoal bg-sniper-charcoal text-white";
  if (actor === "CLIENT_USER") return "border-sniper-green bg-sniper-green-muted text-sniper-charcoal";
  return "border-amber-400 bg-amber-100 text-amber-900";
}

export default function AuditLogPage() {
  const [rows, setRows] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        setRows(await listAuditLogs(300));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load audit logs.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Audit Log</h1>
        <p className="text-app-base text-muted-foreground">Immutable chronology of status changes used for legal compliance and 512(f) defense.</p>
      </header>

      {error ? (
        <section className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-app-sm text-destructive">{error}</section>
      ) : null}

      <section className="audit-watermark overflow-x-auto rounded-md border bg-card shadow-sniper-sm">
        <table className="min-w-full">
          <thead className="bg-muted">
            <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3">Timestamp (ISO)</th>
              <th className="px-4 py-3">Threat ID</th>
              <th className="px-4 py-3">Previous</th>
              <th className="px-4 py-3">New</th>
              <th className="px-4 py-3">Changed By</th>
            </tr>
          </thead>
          <tbody>
            {!loading && rows.length === 0 ? (
              <tr className="border-t bg-white/90">
                <td colSpan={5} className="px-4 py-10 text-center text-app-sm text-muted-foreground">
                  No audit records yet.
                </td>
              </tr>
            ) : null}
            {rows.map((row) => (
              <tr key={row.id} className="border-t bg-white/90">
                <td className="px-4 py-3 font-mono text-app-xs">{new Date(row.changed_at).toISOString()}</td>
                <td className="px-4 py-3 font-mono text-app-xs underline underline-offset-2">{row.threat_id}</td>
                <td className="px-4 py-3">
                  {row.old_status ? (
                    <StatusBadge status={normalizeThreatStatus(row.old_status)} />
                  ) : (
                    <span className="text-app-xs text-muted-foreground">-</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={normalizeThreatStatus(row.new_status)} />
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-sm border px-2 py-1 text-app-xs font-medium ${actorBadgeClass(row.changed_by)}`}>
                    {row.changed_by}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
