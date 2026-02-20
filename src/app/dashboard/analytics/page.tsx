import { formatCurrency } from "@/lib/utils";

const monthly = [
  { month: "Sep", found: 28, removed: 22, revenue: 16400 },
  { month: "Oct", found: 34, removed: 29, revenue: 21700 },
  { month: "Nov", found: 41, removed: 35, revenue: 26200 },
  { month: "Dec", found: 38, removed: 31, revenue: 23200 },
  { month: "Jan", found: 52, removed: 44, revenue: 32900 },
  { month: "Feb", found: 47, removed: 38, revenue: 28400 },
];

export default function AnalyticsPage() {
  const totalRevenue = monthly.reduce((sum, row) => sum + row.revenue, 0);
  const totalFound = monthly.reduce((sum, row) => sum + row.found, 0);
  const totalRemoved = monthly.reduce((sum, row) => sum + row.removed, 0);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Analytics</h1>
        <p className="text-app-base text-muted-foreground">
          Performance summary for discovery and enforcement over the last six months.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <article className="rounded-md border bg-card p-5 shadow-sniper-sm">
          <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Revenue Protected</p>
          <p className="mt-2 font-heading text-app-3xl font-bold">{formatCurrency(totalRevenue)}</p>
        </article>
        <article className="rounded-md border bg-card p-5 shadow-sniper-sm">
          <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Threats Found</p>
          <p className="mt-2 font-heading text-app-3xl font-bold">{totalFound}</p>
        </article>
        <article className="rounded-md border bg-card p-5 shadow-sniper-sm">
          <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Threats Removed</p>
          <p className="mt-2 font-heading text-app-3xl font-bold">{totalRemoved}</p>
        </article>
      </section>

      <section className="rounded-md border bg-card shadow-sniper-sm">
        <table className="min-w-full">
          <thead className="bg-muted">
            <tr className="text-left text-app-xs uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3">Month</th>
              <th className="px-4 py-3">Found</th>
              <th className="px-4 py-3">Removed</th>
              <th className="px-4 py-3">Revenue</th>
            </tr>
          </thead>
          <tbody>
            {monthly.map((row) => (
              <tr key={row.month} className="border-t bg-white">
                <td className="px-4 py-3 text-app-sm font-medium">{row.month}</td>
                <td className="px-4 py-3 text-app-sm">{row.found}</td>
                <td className="px-4 py-3 text-app-sm">{row.removed}</td>
                <td className="px-4 py-3 text-app-sm font-mono">{formatCurrency(row.revenue)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
