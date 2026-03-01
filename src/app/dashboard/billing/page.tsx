"use client";

import { useEffect, useState } from "react";
import { SniperChevron } from "@/components/app/sniper-chevron";
import { createCheckoutSession, listClients } from "@/lib/api";

type Plan = {
  name: string;
  tier: string;
  price: string;
  features: string[];
  contactSales?: boolean;
};

const plans: Plan[] = [
  {
    name: "Starter",
    tier: "STARTER",
    price: "$99/mo",
    features: ["3 Assets", "50 Enforcements/mo", "Daily scanning"],
  },
  {
    name: "Growth",
    tier: "GROWTH",
    price: "$500/mo",
    features: ["Unlimited Assets", "500 Enforcements/mo", "Automated approvals"],
  },
  {
    name: "Agency",
    tier: "AGENCY",
    price: "$1,500/mo",
    features: ["Multi-brand support", "5,000 Enforcements", "API access"],
    contactSales: true,
  },
];

export default function BillingPage() {
  const [currentTier, setCurrentTier] = useState<string>("FREE");
  const [usage, setUsage] = useState(0);
  const [limit, setLimit] = useState(0);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listClients()
      .then((clients) => {
        const client = clients[0];
        if (client) {
          setCurrentTier(client.subscription_tier);
          setUsage(client.current_month_count);
          setLimit(client.monthly_threat_limit);
        }
      })
      .catch(() => setError("Failed to load billing info"))
      .finally(() => setLoading(false));
  }, []);

  async function handleUpgrade(tier: string, contactSales?: boolean) {
    if (contactSales) {
      window.location.href = "mailto:sales@sniperip.com?subject=Agency Plan Inquiry";
      return;
    }
    setUpgrading(tier);
    setError(null);
    try {
      const url = await createCheckoutSession(
        tier,
        `${window.location.origin}/dashboard/billing?success=1`,
        `${window.location.origin}/dashboard/billing?canceled=1`,
      );
      window.location.href = url;
    } catch {
      setError("Failed to start checkout. Please try again.");
      setUpgrading(null);
    }
  }

  const ratio = limit > 0 ? Math.min((usage / limit) * 100, 100) : 0;
  const currentPlan = plans.find((p) => p.tier === currentTier) ?? { name: currentTier, price: "–" };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Billing & Subscription</h1>
        <p className="text-app-base text-muted-foreground">Manage plan limits and upgrade when enforcement demand increases.</p>
      </header>

      {error ? <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p> : null}

      <section className="rounded-md border bg-card p-6 shadow-sniper-sm">
        <p className="text-app-xs uppercase tracking-wider text-muted-foreground">Current Plan</p>
        {loading ? (
          <p className="mt-2 text-app-sm text-muted-foreground">Loading…</p>
        ) : (
          <>
            <h2 className="mt-2 font-heading text-app-2xl font-bold">{currentPlan.name} — {currentPlan.price}</h2>
            <p className="mt-2 text-app-sm text-muted-foreground">{usage} / {limit} takedowns this month</p>
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-sniper-green" style={{ width: `${ratio}%` }} />
            </div>
          </>
        )}
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = plan.tier === currentTier;
          return (
            <article
              key={plan.name}
              className={`rounded-md border p-5 shadow-sniper-sm ${
                isCurrent ? "border-sniper-green bg-sniper-charcoal text-white" : "bg-white"
              }`}
            >
              <div className={isCurrent ? "border-t-4 border-sniper-green pt-3" : "pt-3"}>
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
                  disabled={isCurrent || upgrading !== null}
                  onClick={() => !isCurrent && handleUpgrade(plan.tier, plan.contactSales)}
                  className={`mt-4 inline-flex rounded-md px-3 py-2 text-app-sm font-semibold disabled:opacity-60 ${
                    isCurrent
                      ? "bg-sniper-green text-sniper-charcoal"
                      : "border border-border bg-white text-foreground"
                  }`}
                >
                  {isCurrent
                    ? "Current Plan"
                    : upgrading === plan.tier
                    ? "Redirecting…"
                    : plan.contactSales
                    ? "Contact Sales"
                    : "Upgrade"}
                </button>
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
}
