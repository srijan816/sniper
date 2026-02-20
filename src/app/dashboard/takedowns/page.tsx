import { AlertTriangle } from "lucide-react";
import { StatusBadge } from "@/components/app/status-badge";

const rows = [
  {
    id: "td_1182",
    platform: "Shopify",
    caseNumber: "SH-2026-8894",
    threat: "counterfeit-mall.example.com/premium-sneaker-v2-replica",
    status: "SUBMITTED",
    submittedAt: "2026-02-20T16:12:00Z",
    retry: 0,
  },
  {
    id: "td_1181",
    platform: "Meta",
    caseNumber: "META-661102",
    threat: "instagram.com/p/fakebrand123",
    status: "FAILED",
    submittedAt: "2026-02-20T14:08:00Z",
    retry: 3,
  },
  {
    id: "td_1180",
    platform: "Shopify",
    caseNumber: "SH-2026-8876",
    threat: "fakeshop.example.com/designer-kick-style",
    status: "REMOVED",
    submittedAt: "2026-02-19T22:08:00Z",
    retry: 0,
  },
];

export default function TakedownsPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Takedown Tracking</h1>
        <p className="text-app-base text-muted-foreground">
          Monitor submission status, case numbers, retries, and resolution outcomes.
        </p>
      </header>

      <section className="overflow-x-auto rounded-md border bg-card shadow-sniper-sm">
        <table className="min-w-full">
          <thead className="bg-muted">
            <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3">Platform</th>
              <th className="px-4 py-3">Case Number</th>
              <th className="px-4 py-3">Threat</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Submitted</th>
              <th className="px-4 py-3">Retry</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className={row.status === "FAILED" ? "border-t bg-red-50/50" : "border-t bg-white"}>
                <td className="px-4 py-3 text-app-sm font-medium">{row.platform}</td>
                <td className="px-4 py-3 font-mono text-app-xs">{row.caseNumber}</td>
                <td className="px-4 py-3 text-app-sm text-muted-foreground">{row.threat}</td>
                <td className="px-4 py-3">
                  <div className="inline-flex items-center gap-1">
                    {row.status === "FAILED" ? <AlertTriangle className="h-3.5 w-3.5 text-red-600" /> : null}
                    <StatusBadge status={row.status} />
                  </div>
                </td>
                <td className="px-4 py-3 font-mono text-app-xs text-muted-foreground">{row.submittedAt}</td>
                <td className="px-4 py-3">
                  {row.retry > 0 ? (
                    <span className="rounded-sm bg-amber-100 px-2 py-1 text-app-xs font-medium text-amber-800">
                      Retry {row.retry}/5
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
