import { AlertOctagon, DollarSign, Shield, Users } from "lucide-react";
import { ThreatMetric } from "@/components/app/threat-metric";

const clients = [
  { name: "CoolKicks Co.", plan: "AGENCY", threats: 412, mrr: 1500 },
  { name: "LuxBag Studio", plan: "GROWTH", threats: 287, mrr: 500 },
  { name: "Demo Brand Co.", plan: "GROWTH", threats: 189, mrr: 500 },
  { name: "Streetwear Labs", plan: "STARTER", threats: 48, mrr: 99 },
];

export default function AdminOverviewPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Global Metrics</h1>
        <p className="text-app-base text-muted-foreground">Platform-level visibility across revenue, volume, and operational risk.</p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ThreatMetric label="Total MRR" value="$7,599" delta="+6.1%" icon={DollarSign} positive />
        <ThreatMetric label="Active Clients" value="12" delta="+2" icon={Users} positive />
        <ThreatMetric label="Threats Discovered" value="1,847" delta="+11%" icon={Shield} positive />
        <ThreatMetric label="DLQ Failures" value="2" delta="-1" icon={AlertOctagon} positive={false} />
      </section>

      <section className="overflow-x-auto rounded-md border bg-card shadow-sniper-sm">
        <table className="min-w-full">
          <thead className="bg-muted/40">
            <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3">Client</th>
              <th className="px-4 py-3">Plan</th>
              <th className="px-4 py-3">Threats</th>
              <th className="px-4 py-3">MRR</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr key={client.name} className="border-t bg-card">
                <td className="px-4 py-3 text-app-sm font-medium">{client.name}</td>
                <td className="px-4 py-3 text-app-xs text-muted-foreground">{client.plan}</td>
                <td className="px-4 py-3 font-mono text-app-sm">{client.threats}</td>
                <td className="px-4 py-3 font-mono text-app-sm text-sniper-green">${client.mrr}/mo</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
