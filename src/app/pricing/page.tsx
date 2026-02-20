import Link from "next/link";
import { ChevronIcon } from "@/components/marketing/chevron-icon";
import { PricingGrid } from "@/components/marketing/pricing-grid";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-white text-[#1A1C24]">
      <SiteHeader />
      <main className="mx-auto w-full max-w-7xl px-6 py-14">
        <section className="mb-10 text-center">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[#475569]">
            SniperIP Pricing
          </span>
          <h1 className="mt-2 font-[family-name:var(--font-heading)] text-4xl font-extrabold tracking-tight leading-snug md:text-5xl">
            Enterprise pricing built for automated enforcement.
          </h1>
          <p className="mx-auto mt-4 max-w-3xl text-lg text-[#475569]">
            Start with daily scanning and scale to full automation as your
            product catalog and marketplace exposure expands.
          </p>
        </section>

        <PricingGrid />

        <section className="mt-12 rounded-md border border-[#E2E8F0] bg-[#F8F9FA] p-6 text-center">
          <p className="text-base text-[#475569]">
            Need custom volume, marketplace-specific workflows, or legal ops
            integration?
          </p>
          <Link
            href="/contact"
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-[#10D94B] px-4 py-2 text-sm font-semibold text-[#1A1C24] shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)] transition-all duration-200 ease-out hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2"
          >
            Talk to Sales
            <ChevronIcon className="h-3 w-3" />
          </Link>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
