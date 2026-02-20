import Link from "next/link";
import { Check } from "lucide-react";
import { ChevronIcon } from "@/components/marketing/chevron-icon";
import { pricingTiers } from "@/lib/marketing";

export function PricingGrid() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
      {pricingTiers.map((tier) => (
        <article
          key={tier.name}
          className={`relative rounded-md border p-6 ${
            tier.featured
              ? "-mt-0 border-[#10D94B] bg-white shadow-[0_10px_15px_-3px_rgba(26,28,36,0.08),0_4px_6px_-2px_rgba(26,28,36,0.04)] md:-mt-4"
              : "border-[#E2E8F0] bg-white shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)]"
          }`}
        >
          {tier.featured ? (
            <span className="absolute -top-3 left-5 rounded-full bg-[#10D94B] px-3 py-1 text-xs font-semibold text-[#1A1C24]">
              Most Popular
            </span>
          ) : null}

          <h3 className="font-[family-name:var(--font-heading)] text-2xl font-extrabold tracking-tight text-[#1A1C24]">
            {tier.name}
          </h3>
          <p className="mt-2 min-h-[50px] text-sm text-[#475569]">{tier.description}</p>

          <div className="mt-4 flex items-end gap-1">
            <span className="text-4xl font-extrabold tracking-tight text-[#1A1C24]">
              {tier.price}
            </span>
            {tier.period ? <span className="pb-1 text-sm text-[#475569]">{tier.period}</span> : null}
          </div>

          <ul className="mt-5 space-y-2">
            {tier.features.map((feature) => (
              <li key={feature} className="flex items-start gap-2 text-sm text-[#1A1C24]">
                <Check className="mt-0.5 h-4 w-4 text-[#10D94B]" />
                <span>{feature}</span>
              </li>
            ))}
          </ul>

          <Link
            href={tier.checkoutHref}
            className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-semibold transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2 ${
              tier.featured
                ? "bg-[#1A1C24] text-white hover:scale-105 hover:shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)]"
                : "bg-[#10D94B] text-[#1A1C24] hover:scale-105 hover:shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)]"
            }`}
          >
            {tier.cta}
            <ChevronIcon className="h-3 w-3" />
          </Link>
        </article>
      ))}
    </div>
  );
}
