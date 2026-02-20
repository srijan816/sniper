import { StatusBadge } from "@/components/app/status-badge";

const rows = [
  {
    id: "log_6601",
    timestamp: "2026-02-20T16:12:02.112Z",
    threatId: "th_0024",
    previous: "DISCOVERED",
    next: "PENDING_APPROVAL",
    actor: "CLIENT",
  },
  {
    id: "log_6602",
    timestamp: "2026-02-20T16:14:05.008Z",
    threatId: "th_0024",
    previous: "PENDING_APPROVAL",
    next: "SUBMITTED",
    actor: "SYSTEM",
  },
  {
    id: "log_6603",
    timestamp: "2026-02-20T16:50:44.118Z",
    threatId: "th_0024",
    previous: "SUBMITTED",
    next: "REMOVED",
    actor: "SYSTEM",
  },
];

export default function AuditLogPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Audit Log</h1>
        <p className="text-app-base text-muted-foreground">
          Immutable chronology of status changes used for legal compliance and 512(f) defense.
        </p>
      </header>

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
            {rows.map((row) => (
              <tr key={row.id} className="border-t bg-white/90">
                <td className="px-4 py-3 font-mono text-app-xs">{row.timestamp}</td>
                <td className="px-4 py-3 font-mono text-app-xs underline underline-offset-2">{row.threatId}</td>
                <td className="px-4 py-3"><StatusBadge status={row.previous} /></td>
                <td className="px-4 py-3"><StatusBadge status={row.next} /></td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-sm border px-2 py-1 text-app-xs font-medium ${
                      row.actor === "SYSTEM"
                        ? "border-sniper-charcoal bg-sniper-charcoal text-white"
                        : row.actor === "CLIENT"
                          ? "border-sniper-green bg-sniper-green-muted text-sniper-charcoal"
                          : "border-amber-400 bg-amber-100 text-amber-900"
                    }`}
                  >
                    {row.actor}
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
