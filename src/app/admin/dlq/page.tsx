"use client";

import { useState } from "react";

type DLQEntry = {
  id: string;
  platform: string;
  threatUrl: string;
  reason: string;
  stack: string;
};

const seed: DLQEntry[] = [
  {
    id: "dlq_9001",
    platform: "Shopify",
    threatUrl: "counterfeit-mall.example.com/premium-sneaker-v2-replica",
    reason: "Timeout on submit button after 5 retries",
    stack: "TimeoutError: submit selector not found at playwright-worker/shopify.ts:144",
  },
  {
    id: "dlq_9002",
    platform: "Meta",
    threatUrl: "instagram.com/p/fakebrand123",
    reason: "API 403 rate limit exceeded",
    stack: "HTTPError 403 at services/meta-client.ts:88",
  },
];

export default function AdminDLQPage() {
  const [rows, setRows] = useState(seed);

  const rerun = (id: string) => {
    setRows((prev) => prev.filter((row) => row.id !== id));
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Dead Letter Queue</h1>
        <p className="text-app-base text-muted-foreground">Failed automation tasks requiring manual intervention and reruns.</p>
      </header>

      <section className="overflow-x-auto rounded-md border bg-card shadow-sniper-sm">
        <table className="min-w-full">
          <thead className="bg-muted/40">
            <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3">Platform</th>
              <th className="px-4 py-3">Threat URL</th>
              <th className="px-4 py-3">Error Reason</th>
              <th className="px-4 py-3">Stack Trace</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t bg-card">
                <td className="px-4 py-3 text-app-sm font-medium">{row.platform}</td>
                <td className="px-4 py-3 font-mono text-app-xs text-muted-foreground">{row.threatUrl}</td>
                <td className="px-4 py-3 text-app-sm text-red-300">{row.reason}</td>
                <td className="px-4 py-3 font-mono text-app-xs text-muted-foreground">{row.stack}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => rerun(row.id)}
                    className="rounded-md bg-sniper-green px-3 py-2 text-app-sm font-semibold text-sniper-charcoal"
                  >
                    Re-run
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
