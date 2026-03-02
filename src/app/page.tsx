"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { CheckCircle2, Eye, Radar, Workflow } from "lucide-react";
import { ChevronIcon } from "@/components/marketing/chevron-icon";
import { PricingGrid } from "@/components/marketing/pricing-grid";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { FreeScan } from "@/components/FreeScan";

type DemoState = "idle" | "submitted";

const monitoringPlatforms = ["Shopify", "Meta", "TikTok", "Amazon"];

const howSteps = [
  {
    title: "Ingest",
    body: "Upload visual assets. Our Vision-Language Models map the semantic DNA of your products.",
    icon: Eye,
  },
  {
    title: "Monitor",
    body: "Continuous scanning across global e-commerce and social footprints.",
    icon: Radar,
  },
  {
    title: "Enforce",
    body: "One-click, legally compliant takedowns powered by headless automation.",
    icon: Workflow,
  },
] as const;

const techCards = [
  {
    title: "SigLIP 2 Vision AI",
    body: "Catches fakes even when infringers crop, color-shift, or watermark the original creative.",
  },
  {
    title: "512(f) Safe Harbor",
    body: "Every action is backed by digitally executed LOAs and an immutable audit trail, reducing legal risk from false claims.",
  },
  {
    title: "Playwright RPA Automation",
    body: "Headless workflows resolve repetitive abuse-form submissions across platform-specific reporting flows.",
  },
  {
    title: "Dynamic Whitelisting",
    body: "Granular domain controls keep authorized distributors and wholesale partners out of enforcement queues.",
  },
] as const;

export default function MarketingHomePage() {
  const [demoState, setDemoState] = useState<DemoState>("idle");

  useEffect(() => {
    if (demoState !== "submitted") {
      return;
    }

    const id = window.setTimeout(() => setDemoState("idle"), 2800);
    return () => window.clearTimeout(id);
  }, [demoState]);

  return (
    <div className="min-h-screen bg-white text-[#1A1C24]">
      <SiteHeader />

      <main>
        <section className="mx-auto w-full max-w-7xl px-6 pb-14 pt-12">
          <div className="flex flex-col gap-10 lg:grid lg:grid-cols-12 lg:items-center">
            <div className="lg:col-span-6">
              <h1 className="font-[family-name:var(--font-heading)] text-5xl font-extrabold leading-tight tracking-tight md:text-6xl">
                Automated IP Protection for D2C Brands.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-[1.6] text-[#475569] md:text-xl">
                Identify and neutralize counterfeit products across Shopify,
                Meta, and global marketplaces in under 24 hours.
                Enterprise-grade DMCA enforcement at machine speed.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/auth/login"
                  aria-label="Start free SniperIP scan"
                  className="inline-flex items-center gap-2 rounded-md bg-[#10D94B] px-5 py-3 text-sm font-semibold text-[#1A1C24] shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)] transition-all duration-200 ease-out hover:scale-105 hover:shadow-[0_10px_15px_-3px_rgba(26,28,36,0.08),0_4px_6px_-2px_rgba(26,28,36,0.04)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2"
                >
                  Start Free Scan
                  <ChevronIcon className="h-3 w-3" />
                </Link>
                <Link
                  href="/pricing"
                  aria-label="View SniperIP pricing"
                  className="inline-flex items-center gap-2 rounded-md border border-[#E2E8F0] bg-white px-5 py-3 text-sm font-semibold text-[#1A1C24] transition-all duration-200 ease-out hover:border-[#1A1C24] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2"
                >
                  View Pricing
                </Link>
              </div>
            </div>

            <div className="lg:col-span-6">
              <div className="overflow-hidden rounded-md border border-[#E2E8F0] bg-white shadow-[0_10px_15px_-3px_rgba(26,28,36,0.08),0_4px_6px_-2px_rgba(26,28,36,0.04)]">
                <Image
                  src="/generated/1.png"
                  alt="SniperIP dashboard showing automated threat detection and enforcement workflow"
                  width={1600}
                  height={1000}
                  priority
                  className="h-auto w-full"
                />
              </div>
            </div>
          </div>

          <div className="mt-10 rounded-md border border-[#E2E8F0] bg-[#F8F9FA] px-4 py-4 text-center">
            <p className="text-sm font-medium text-[#1A1C24]">
              Protecting Revenue for Top D2C Brands
            </p>
            <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
              {monitoringPlatforms.map((platform) => (
                <span
                  key={platform}
                  className="rounded-md border border-[#E2E8F0] bg-white px-3 py-1 text-xs text-[#475569]"
                >
                  {platform}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-[#F8F9FA]">
          <div className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-10 px-6 py-16 md:grid-cols-2 md:items-center">
            <div className="space-y-3">
              <article className="rounded-md border border-[#E2E8F0] bg-white p-4 shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)]">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#475569]">
                  Original Product Render
                </p>
                <div className="h-24 rounded-md border border-[#E2E8F0] bg-gradient-to-r from-slate-900 to-slate-700" />
              </article>

              {["Counterfeit Listing A", "Counterfeit Listing B", "Counterfeit Listing C"].map(
                (label) => (
                  <article
                    key={label}
                    className="rounded-md border border-[#E2E8F0] bg-white p-4"
                  >
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#475569]">
                      {label}
                    </p>
                    <div className="relative h-16 rounded-md border border-red-500/70 bg-slate-100">
                      <span className="absolute right-2 top-2 rounded-sm bg-red-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                        Infringement Detected
                      </span>
                    </div>
                  </article>
                ),
              )}
            </div>

            <div>
              <h2 className="font-[family-name:var(--font-heading)] text-4xl font-extrabold leading-snug tracking-tight md:text-5xl">
                Viral success invites instant theft.
              </h2>
              <p className="mt-5 text-base leading-[1.6] text-[#475569]">
                While traditional counsel takes weeks to draft notices,
                SniperIP continuously maps your visual assets and surgically
                enforces your rights the moment a clone appears.
              </p>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="mx-auto w-full max-w-7xl px-6 py-16">
          <div className="mb-10 text-center">
            <h2 className="font-[family-name:var(--font-heading)] text-4xl font-extrabold leading-snug tracking-tight md:text-5xl">
              How SniperIP Works
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {howSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <article
                  key={step.title}
                  className="rounded-md border border-[#E2E8F0] bg-white p-6 shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)] transition-all duration-200 ease-out hover:shadow-[0_10px_15px_-3px_rgba(26,28,36,0.08),0_4px_6px_-2px_rgba(26,28,36,0.04)]"
                >
                  <div className="mb-3 inline-flex items-center gap-2 rounded-md border border-[#E2E8F0] bg-[#F8F9FA] px-2.5 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-[#475569]">
                    {index === 2 ? (
                      <ChevronIcon className="h-3 w-3 text-[#1A1C24]" />
                    ) : (
                      <Icon className="h-4 w-4 text-[#1A1C24]" />
                    )}
                    {step.title}
                  </div>
                  <p className="text-base text-[#475569]">{step.body}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section id="demo" className="bg-[#1A1C24]">
          <div className="mx-auto w-full max-w-7xl px-6 py-16">
            <div className="mb-8 text-center">
              <h2 className="font-[family-name:var(--font-heading)] text-4xl font-extrabold leading-snug tracking-tight text-white md:text-5xl">
                Experience the SniperIP Dashboard.
              </h2>
            </div>

            <div className="relative overflow-hidden rounded-md border border-white/20 bg-[#10131B] p-4 shadow-[0_10px_15px_-3px_rgba(26,28,36,0.08),0_4px_6px_-2px_rgba(26,28,36,0.04)] md:p-6">
              <Image
                src="/generated/2.png"
                alt="Threat inbox demo with original and counterfeit listing comparison"
                width={1600}
                height={1000}
                className="h-auto w-full rounded-md border border-white/15"
              />

              <div className="mt-5 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  aria-label="Approve takedown action in demo"
                  onClick={() => setDemoState("submitted")}
                  className="inline-flex items-center gap-2 rounded-md bg-[#10D94B] px-5 py-3 text-sm font-semibold text-[#1A1C24] transition-all duration-200 ease-out hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2 focus-visible:ring-offset-[#1A1C24]"
                >
                  Approve Takedown
                  <ChevronIcon className="h-3 w-3" />
                </button>
                {demoState === "submitted" ? (
                  <div className="inline-flex items-center gap-2 rounded-md border border-[#10D94B]/40 bg-[#10D94B]/15 px-3 py-2 text-sm text-white">
                    <CheckCircle2 className="h-4 w-4 text-[#10D94B]" />
                    Enforcement Action Submitted
                  </div>
                ) : (
                  <p className="text-sm text-white/70">
                    Review evidence, approve enforcement, and keep the workflow auditable.
                  </p>
                )}
              </div>
            </div>
          </div>
        </section>

        <section id="technology" className="bg-[#F8F9FA]">
          <div className="mx-auto w-full max-w-7xl px-6 py-16">
            <div className="mb-10 text-center">
              <h2 className="font-[family-name:var(--font-heading)] text-4xl font-extrabold leading-snug tracking-tight md:text-5xl">
                Tech Moat & Legal Security
              </h2>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {techCards.map((card) => (
                <article
                  key={card.title}
                  className="rounded-md border border-[#E2E8F0] bg-white p-6 shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)]"
                >
                  <h3 className="font-[family-name:var(--font-heading)] text-2xl font-extrabold tracking-tight text-[#1A1C24]">
                    {card.title}
                  </h3>
                  <p className="mt-3 text-base leading-[1.6] text-[#475569]">
                    {card.body}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="free-scan" className="mx-auto w-full max-w-7xl px-6 py-16">
          <div className="mb-10 text-center">
            <h2 className="font-[family-name:var(--font-heading)] text-4xl font-extrabold leading-snug tracking-tight md:text-5xl">
              Try a Free Brand Scan
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-base text-[#475569]">
              Upload a product image to instantly detect counterfeits across global marketplaces. No account required.
            </p>
          </div>
          <FreeScan />
        </section>

        <section id="pricing" className="mx-auto w-full max-w-7xl px-6 py-16">
          <div className="mb-10 text-center">
            <h2 className="font-[family-name:var(--font-heading)] text-4xl font-extrabold leading-snug tracking-tight md:text-5xl">
              Pricing
            </h2>
          </div>
          <PricingGrid />
        </section>

        <section className="bg-[#1A1C24]">
          <div className="mx-auto w-full max-w-7xl px-6 py-16 text-center">
            <h2 className="font-[family-name:var(--font-heading)] text-4xl font-extrabold leading-snug tracking-tight text-white md:text-5xl">
              Ready to reclaim your revenue?
            </h2>
            <p className="mx-auto mt-4 max-w-3xl text-base text-[#94A3B8] md:text-lg">
              Move from manual legal operations to an automated enforcement
              workflow designed for scale, speed, and auditability.
            </p>
            <Link
              href="/auth/login"
              aria-label="Protect my brand now"
              className="mt-7 inline-flex items-center gap-2 rounded-md bg-[#10D94B] px-6 py-3 text-sm font-semibold text-[#1A1C24] shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)] transition-all duration-200 ease-out hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10D94B] focus-visible:ring-offset-2 focus-visible:ring-offset-[#1A1C24]"
            >
              Protect My Brand Now
              <ChevronIcon className="h-3 w-3" />
            </Link>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
