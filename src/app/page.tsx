"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  FileCheck2,
  Radar,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import { PricingGrid } from "@/components/marketing/pricing-grid";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { FreeScan } from "@/components/FreeScan";

type DispatchState = "idle" | "queued";

const heroStats = [
  { label: "median takedown start", value: "< 24 hrs" },
  { label: "evidence trail", value: "immutable" },
  { label: "review mode", value: "human-in-loop" },
] as const;

const operatingLoop = [
  {
    step: "01",
    title: "Map your canon",
    body: "Upload campaign renders, PDP imagery, and video. SniperIP fingerprints every asset before it goes live.",
    icon: Sparkles,
  },
  {
    step: "02",
    title: "Hunt marketplace drift",
    body: "Radar sweeps open web, social commerce, and marketplace copies while respecting partner whitelists.",
    icon: Radar,
  },
  {
    step: "03",
    title: "File with receipts",
    body: "The enforcement queue ships every takedown with the supporting evidence packet, contact metadata, and audit trail.",
    icon: Workflow,
  },
] as const;

const proofCards = [
  {
    eyebrow: "Threat inbox",
    title: "A queue designed for brand operators, not AI tourists.",
    body: "The UI is tuned for decision velocity: approve, whitelist, or escalate without losing the forensic trail behind each call.",
  },
  {
    eyebrow: "Legal posture",
    title: "Every action is documented for defensibility.",
    body: "LOAs, contact metadata, and timestamped audit events keep enforcement fast without becoming legally sloppy.",
  },
  {
    eyebrow: "Coverage",
    title: "Built for the channels where clones actually spread.",
    body: "Shopify storefronts, Meta surfaces, Amazon-style marketplaces, and long-tail domains sit in the same enforcement system.",
  },
] as const;

const signalRows = [
  { label: "Signal", value: "Visual similarity, host history, seller fingerprints" },
  { label: "Decision", value: "Approve, suppress, or auto-route by threshold" },
  { label: "Output", value: "Platform filing, evidence locker, notification dispatch" },
] as const;

export default function MarketingHomePage() {
  const [dispatchState, setDispatchState] = useState<DispatchState>("idle");

  useEffect(() => {
    if (dispatchState !== "queued") {
      return;
    }

    const timeout = window.setTimeout(() => setDispatchState("idle"), 2800);
    return () => window.clearTimeout(timeout);
  }, [dispatchState]);

  return (
    <div className="min-h-screen bg-[#f3efe3] text-[#141315]">
      <SiteHeader />

      <main className="overflow-hidden">
        <section className="relative border-b border-[#141315]/10">
          <div className="absolute inset-0 tactical-grid opacity-40" />
          <div className="absolute left-[-8rem] top-20 h-64 w-64 rounded-full bg-[#10D94B]/10 blur-3xl" />
          <div className="absolute right-[-6rem] top-12 h-72 w-72 rounded-full bg-[#c9783b]/15 blur-3xl" />

          <div className="relative mx-auto grid w-full max-w-7xl gap-12 px-6 pb-16 pt-12 lg:grid-cols-[1.08fr_0.92fr] lg:items-center lg:pb-24 lg:pt-16">
            <div>
              <div className="inline-flex items-center gap-3 rounded-full border border-[#141315]/12 bg-white/70 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#5d5b57]">
                <span className="marketing-status-dot h-2 w-2 rounded-full bg-[#10D94B]" />
                Counterfeit enforcement operating system
              </div>

              <h1 className="mt-6 max-w-4xl font-[family-name:var(--font-heading)] text-5xl font-bold leading-[0.94] tracking-[-0.05em] md:text-7xl">
                Protect the product before copycats turn your growth into their margin.
              </h1>

              <p className="mt-6 max-w-2xl text-lg leading-8 text-[#4f4b44] md:text-xl">
                SniperIP gives D2C teams a live enforcement desk: visual monitoring, threat review, evidence packaging, and takedown execution in one system.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/auth/login"
                  className="inline-flex items-center gap-2 rounded-full bg-[#141315] px-6 py-3 text-sm font-semibold text-[#f3efe3] transition hover:-translate-y-0.5"
                >
                  Start Free Scan
                  <ChevronRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center gap-2 rounded-full border border-[#141315]/12 bg-white/70 px-6 py-3 text-sm font-semibold text-[#141315] transition hover:border-[#141315]"
                >
                  Review Plans
                  <ArrowUpRight className="h-4 w-4" />
                </Link>
              </div>

              <div className="mt-10 grid gap-3 sm:grid-cols-3">
                {heroStats.map((item) => (
                  <div key={item.label} className="signal-frame rounded-3xl border border-[#141315]/10 bg-white/80 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#6b675f]">{item.label}</p>
                    <p className="mt-2 text-2xl font-semibold text-[#141315]">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="marketing-float">
              <div className="signal-frame relative overflow-hidden rounded-[2rem] border border-[#141315]/12 bg-[#141315] p-5 text-white">
                <div className="marketing-sweep absolute inset-0 opacity-70" />
                <div className="relative">
                  <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                    <div>
                      <p className="text-[11px] uppercase tracking-[0.18em] text-white/60">Evidence board</p>
                      <p className="mt-1 text-lg font-semibold">High-confidence listing detected</p>
                    </div>
                    <div className="rounded-full bg-[#10D94B]/15 px-3 py-1 text-xs font-semibold text-[#9ef0ba]">
                      94% match
                    </div>
                  </div>

                  <div className="mt-4 overflow-hidden rounded-[1.4rem] border border-white/10 bg-[#211f26]">
                    <Image
                      src="/hero-dashboard.webp"
                      alt="SniperIP dashboard showing enforcement operations"
                      width={1600}
                      height={1100}
                      priority
                      className="h-auto w-full"
                    />
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-white/55">Escalation path</p>
                      <p className="mt-2 text-sm leading-6 text-white/80">
                        Storefront copy detected on an unauthorized domain with repeat seller fingerprints and price compression.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setDispatchState("queued")}
                      className="rounded-2xl border border-[#10D94B]/35 bg-[#10D94B]/12 p-4 text-left transition hover:border-[#10D94B]/60"
                    >
                      <p className="text-[11px] uppercase tracking-[0.18em] text-[#9ef0ba]">Operator action</p>
                      <div className="mt-2 flex items-center justify-between">
                        <p className="text-lg font-semibold">
                          {dispatchState === "queued" ? "Takedown queued" : "Approve filing"}
                        </p>
                        {dispatchState === "queued" ? (
                          <CheckCircle2 className="h-5 w-5 text-[#9ef0ba]" />
                        ) : (
                          <FileCheck2 className="h-5 w-5 text-[#9ef0ba]" />
                        )}
                      </div>
                      <p className="mt-2 text-sm text-white/75">
                        {dispatchState === "queued"
                          ? "Evidence packet and notification dispatch are in motion."
                          : "Create the platform request with a complete evidence packet."}
                      </p>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-b border-[#141315]/10">
          <div className="mx-auto w-full max-w-7xl px-6 py-20 md:py-24">
            <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#6b675f]">Operator loop</p>
                <h2 className="mt-4 max-w-xl font-[family-name:var(--font-heading)] text-4xl font-bold tracking-[-0.04em] md:text-5xl">
                  A measured workflow built to keep enforcement fast and defensible.
                </h2>
              </div>

              <div className="grid gap-4">
                {operatingLoop.map((item) => {
                  const Icon = item.icon;
                  return (
                    <article
                      key={item.title}
                      className="signal-frame rounded-[1.6rem] border border-[#141315]/10 bg-white/80 p-6"
                    >
                      <div className="flex items-start gap-4">
                        <div className="rounded-2xl border border-[#141315]/10 bg-[#f7f2e8] px-3 py-2 text-sm font-semibold text-[#141315]">
                          {item.step}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-3">
                            <Icon className="h-5 w-5 text-[#10D94B]" />
                            <h3 className="text-2xl font-semibold">{item.title}</h3>
                          </div>
                          <p className="mt-3 max-w-2xl text-base leading-7 text-[#5c5851]">{item.body}</p>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        <section id="technology" className="bg-[#141315] text-white">
          <div className="mx-auto grid w-full max-w-7xl gap-10 px-6 py-20 md:py-24 lg:grid-cols-[0.92fr_1.08fr]">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-white/55">Proof stack</p>
              <h2 className="mt-4 font-[family-name:var(--font-heading)] text-4xl font-bold tracking-[-0.04em] md:text-5xl">
                The moat is not the model. It is the evidence discipline around the model.
              </h2>
              <p className="mt-5 max-w-xl text-lg leading-8 text-white/72">
                Better scanning only matters if the downstream case packet, legal contact layer, and operator review path hold together under pressure.
              </p>

              <div className="mt-8 space-y-3">
                {signalRows.map((row) => (
                  <div key={row.label} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/50">{row.label}</p>
                    <p className="mt-2 text-sm leading-6 text-white/80">{row.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {proofCards.map((card, index) => (
                <article
                  key={card.title}
                  className={`rounded-[1.8rem] border border-white/10 p-6 ${
                    index === 1 ? "bg-[#10D94B]/10" : "bg-white/6"
                  }`}
                >
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/55">{card.eyebrow}</p>
                  <h3 className="mt-4 text-2xl font-semibold">{card.title}</h3>
                  <p className="mt-3 text-base leading-7 text-white/74">{card.body}</p>
                </article>
              ))}

              <div className="rounded-[1.8rem] border border-[#10D94B]/20 bg-[#0c2614] p-6 md:col-span-2">
                <div className="flex flex-wrap items-center gap-3">
                  <ShieldAlert className="h-5 w-5 text-[#9ef0ba]" />
                  <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#9ef0ba]">Built for counterfeit response</p>
                </div>
                <p className="mt-4 max-w-3xl text-xl leading-8 text-white/85">
                  SniperIP is opinionated about the real job: move from suspicion to documented enforcement without losing chain-of-custody or flooding your team with noise.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section id="demo" className="border-b border-[#141315]/10">
          <div className="mx-auto grid w-full max-w-7xl gap-10 px-6 py-20 md:py-24 lg:grid-cols-[0.78fr_1.22fr]">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#6b675f]">Free scan</p>
              <h2 className="mt-4 font-[family-name:var(--font-heading)] text-4xl font-bold tracking-[-0.04em] md:text-5xl">
                Drop in a hero image. See the counterfeit surface around it.
              </h2>
              <p className="mt-5 max-w-xl text-lg leading-8 text-[#5c5851]">
                The free scan is designed as a sharp diagnostic, not a lead-gen gimmick. It shows where your product imagery is being mirrored and how risky the matches look.
              </p>

              <div className="mt-8 rounded-[1.6rem] border border-[#141315]/10 bg-white/70 p-5">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-5 w-5 text-[#10D94B]" />
                  <p className="text-sm font-semibold text-[#141315]">What comes back</p>
                </div>
                <ul className="mt-4 space-y-3 text-sm leading-6 text-[#5c5851]">
                  <li>Blurred marketplace previews and domain hints so teams can triage safely.</li>
                  <li>Similarity scoring that ranks where enforcement should begin.</li>
                  <li>A clean next step into the authenticated threat inbox when you are ready.</li>
                </ul>
              </div>
            </div>

            <div className="signal-frame rounded-[2rem] border border-[#141315]/10 bg-white/82 p-6">
              <FreeScan />
            </div>
          </div>
        </section>

        <section className="bg-[#ede6d6]">
          <div className="mx-auto w-full max-w-7xl px-6 py-20 md:py-24">
            <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#6b675f]">Plans</p>
                <h2 className="mt-4 font-[family-name:var(--font-heading)] text-4xl font-bold tracking-[-0.04em] md:text-5xl">
                  Choose the operating mode that matches your enforcement volume.
                </h2>
              </div>
              <Link href="/auth/login" className="inline-flex items-center gap-2 text-sm font-semibold text-[#141315]">
                Launch workspace
                <ArrowUpRight className="h-4 w-4" />
              </Link>
            </div>

            <PricingGrid />
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
