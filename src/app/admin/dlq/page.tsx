"use client";

import { useEffect, useState } from "react";
import { dismissDlqEntry, getAdminDlq, retryDlqEntry } from "@/lib/api";

type DLQEntry = {
  id: string;
  takedown_id?: string;
  error_reason: string;
  failed_at: string;
};

export default function AdminDLQPage() {
  const [rows, setRows] = useState<DLQEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null);

  useEffect(() => {
    getAdminDlq()
      .then(setRows)
      .catch(() => setError("Failed to load DLQ — are you signed in as an admin?"))
      .finally(() => setLoading(false));
  }, []);

  async function handleRetry(id: string) {
    setActing(id);
    try {
      await retryDlqEntry(id);
      setRows((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setError(`Failed to retry entry ${id}`);
    } finally {
      setActing(null);
    }
  }

  async function handleDismiss(id: string) {
    setActing(id);
    try {
      await dismissDlqEntry(id);
      setRows((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setError(`Failed to dismiss entry ${id}`);
    } finally {
      setActing(null);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Dead Letter Queue</h1>
        <p className="text-app-base text-muted-foreground">Failed automation tasks requiring manual intervention and reruns.</p>
      </header>

      {error ? <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p> : null}

      {loading ? (
        <p className="text-app-sm text-muted-foreground">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="rounded-md border bg-card p-6 text-center text-app-sm text-muted-foreground">No failed entries in the queue.</p>
      ) : (
        <section className="overflow-x-auto rounded-md border bg-card shadow-sniper-sm">
          <table className="min-w-full">
            <thead className="bg-muted/40">
              <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-3">Takedown ID</th>
                <th className="px-4 py-3">Error Reason</th>
                <th className="px-4 py-3">Failed At</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t bg-card">
                  <td className="px-4 py-3 font-mono text-app-xs text-muted-foreground">{row.takedown_id ?? row.id}</td>
                  <td className="px-4 py-3 text-app-sm text-red-600">{row.error_reason}</td>
                  <td className="px-4 py-3 text-app-xs text-muted-foreground">{new Date(row.failed_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex gap-2">
                      <button
                        type="button"
                        disabled={acting === row.id}
                        onClick={() => handleRetry(row.id)}
                        className="rounded-md bg-sniper-green px-3 py-2 text-app-sm font-semibold text-sniper-charcoal disabled:opacity-60"
                      >
                        {acting === row.id ? "…" : "Re-run"}
                      </button>
                      <button
                        type="button"
                        disabled={acting === row.id}
                        onClick={() => handleDismiss(row.id)}
                        className="rounded-md border px-3 py-2 text-app-sm font-medium disabled:opacity-60"
                      >
                        Dismiss
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
