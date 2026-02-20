const domains = ["authorized-retailer.example.com", "wholesale-partner.example.com", "brand-owned-shopify.example.com"];

export default function WhitelistPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Whitelist</h1>
        <p className="text-app-base text-muted-foreground">Protect authorized distributors from accidental enforcement.</p>
      </header>

      <section className="rounded-md border bg-card p-6 shadow-sniper-sm">
        <ul className="space-y-2">
          {domains.map((domain) => (
            <li key={domain} className="rounded-sm border bg-white px-3 py-2 font-mono text-app-sm">
              {domain}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
