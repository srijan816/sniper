import { SniperChevron } from "@/components/app/sniper-chevron";

const plans = [
  {
    name: "Starter",
    price: "$99/mo",
    current: false,
    features: ["3 Assets", "50 Enforcements/mo", "Daily scanning"],
  },
  {
    name: "Growth",
    price: "$500/mo",
    current: true,
    features: ["Unlimited Assets", "500 Enforcements/mo", "Automated approvals"],
  },
  {
    name: "Agency",
    price: "$1,500/mo",
    current: false,
    features: ["Multi-brand support", "5,000 Enforcements", "API access"],
  },
];

export default function BillingPage() {
  const usage = 142;
  const limit = 500;
  const ratio = Math.min((usage / limit) * 100, 100);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Billing & Subscription</h1>
        <p className="text-app-base text-muted-foreground">Manage plan limits and upgrade when enforcement demand increases.</p>
      </header>

      <section className="rounded-md border bg-card p-6 shadow-sniper-sm">
        <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Current Plan</p>
        <h2 className="mt-2 font-heading text-app-2xl font-bold">Growth — $500/mo</h2>
        <p className="mt-2 text-app-sm text-muted-foreground">{usage} / {limit} takedowns this month</p>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-sniper-green" style={{ width: `${ratio}%` }} />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {plans.map((plan) => (
          <article
            key={plan.name}
            className={`rounded-md border p-5 shadow-sniper-sm ${
              plan.name === "Growth" ? "border-sniper-green bg-sniper-charcoal text-white" : "bg-white"
            }`}
          >
            <div className={plan.name === "Growth" ? "border-t-4 border-sniper-green pt-3" : "pt-3"}>
              <h3 className="font-heading text-app-xl font-semibold">{plan.name}</h3>
              <p className="mt-1 text-app-lg font-bold">{plan.price}</p>
              <ul className="mt-3 space-y-2">
                {plan.features.map((feature) => (
                  <li key={feature} className="inline-flex items-center gap-2 text-app-sm">
                    <SniperChevron className="h-3 w-3 text-sniper-green" />
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className={`mt-4 inline-flex rounded-md px-3 py-2 text-app-sm font-semibold ${
                  plan.current
                    ? "bg-sniper-green text-sniper-charcoal"
                    : "border border-border bg-white text-foreground"
                }`}
              >
                {plan.current ? "Current Plan" : plan.name === "Agency" ? "Contact Sales" : "Upgrade"}
              </button>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
