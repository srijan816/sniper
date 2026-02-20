import Link from "next/link";
import { AlertTriangle, Clock3, ShieldCheck, TrendingUp } from "lucide-react";
import { ThreatMetric } from "@/components/app/threat-metric";
import { StatusBadge } from "@/components/app/status-badge";

const recentThreats = [
  {
    id: "th_0097",
    domain: "counterfeit-mall.example.com",
    url: "https://counterfeit-mall.example.com/sneaker-deal",
    score: 97,
    status: "PENDING_APPROVAL",
    discovered: "2h ago",
  },
  {
    id: "th_0096",
    domain: "fakeshop.example.com",
    url: "https://fakeshop.example.com/premium-sneaker-v2-replica",
    score: 96,
    status: "SUBMITTED",
    discovered: "3h ago",
  },
  {
    id: "th_0095",
    domain: "wish-deals.example.com",
    url: "https://wish-deals.example.com/sneaker-cheap",
    score: 95,
    status: "REMOVED",
    discovered: "1d ago",
  },
];

export default function DashboardOverviewPage() {
  return (
    <div className="space-y-app-section">
      <section className="rounded-md border bg-card p-6 shadow-sniper-md">
        <p className="text-app-sm text-muted-foreground">This month</p>
        <h1 className="mt-1 font-heading text-app-2xl font-bold text-foreground">
          47 threats found → $28,400 estimated revenue protected
        </h1>
        <p className="mt-2 text-app-base text-muted-foreground">
          Based on 38 removals and your configured average order value.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ThreatMetric label="Threats Discovered" value="47" delta="+12%" icon={AlertTriangle} positive />
        <ThreatMetric label="Threats Removed" value="38" delta="+8%" icon={ShieldCheck} positive />
        <ThreatMetric label="Revenue Protected" value="$28.4k" delta="+17%" icon={TrendingUp} positive />
        <ThreatMetric label="Pending Review" value="3" icon={Clock3} />
      </section>

      <section className="rounded-md border bg-card shadow-sniper-sm">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="font-heading text-app-xl font-semibold">Recent threats</h2>
          <Link href="/dashboard/threats" className="text-app-sm font-medium text-foreground underline-offset-2 hover:underline">
            Open inbox
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-muted">
              <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
                <th className="px-5 py-3">Domain</th>
                <th className="px-5 py-3">URL</th>
                <th className="px-5 py-3">Similarity</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Discovered</th>
              </tr>
            </thead>
            <tbody>
              {recentThreats.map((threat) => (
                <tr key={threat.id} className="border-t bg-white transition hover:bg-muted/60">
                  <td className="px-5 py-3 text-app-base font-medium text-foreground">{threat.domain}</td>
                  <td className="px-5 py-3 font-mono text-app-xs text-muted-foreground">{threat.url}</td>
                  <td className="px-5 py-3 font-mono text-app-sm text-foreground">{threat.score}%</td>
                  <td className="px-5 py-3"><StatusBadge status={threat.status} /></td>
                  <td className="px-5 py-3 text-app-sm text-muted-foreground">{threat.discovered}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
