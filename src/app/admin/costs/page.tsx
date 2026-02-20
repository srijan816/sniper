const costs = [
  { label: "SerpApi Credits", used: 4230, limit: 10000, spend: 89.0 },
  { label: "HuggingFace Compute", used: 12.4, limit: 50, spend: 18.6 },
  { label: "ZenRows Bandwidth (MB)", used: 847, limit: 2000, spend: 42.36 },
];

function getTone(percent: number) {
  if (percent >= 100) return "bg-red-500";
  if (percent >= 80) return "bg-amber-500";
  return "bg-sniper-green";
}

export default function AdminCostsPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Cost Monitoring</h1>
        <p className="text-app-base text-muted-foreground">Track infrastructure cost against budget and margin targets.</p>
      </header>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {costs.map((cost) => {
          const percent = Math.min((cost.used / cost.limit) * 100, 100);
          return (
            <article key={cost.label} className="rounded-md border bg-card p-5 shadow-sniper-sm">
              <h2 className="font-heading text-app-lg font-semibold">{cost.label}</h2>
              <p className="mt-1 font-mono text-app-sm text-muted-foreground">
                {cost.used.toLocaleString()} / {cost.limit.toLocaleString()}
              </p>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
                <div className={`h-full ${getTone(percent)}`} style={{ width: `${percent}%` }} />
              </div>
              <p className="mt-2 font-mono text-app-sm">${cost.spend.toFixed(2)} spend</p>
              <p className="text-app-xs text-muted-foreground">{percent.toFixed(1)}% of budget</p>
            </article>
          );
        })}
      </section>
    </div>
  );
}
