"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, ArrowRight, CheckCircle2, CreditCard, FileSignature, Mail, Upload } from "lucide-react";
import { useState } from "react";
import { SniperChevron } from "@/components/app/sniper-chevron";
import { useOnboardingStore } from "@/lib/store";
import { createCheckoutSession } from "@/lib/api";

const steps = [
  { title: "Account", icon: Mail },
  { title: "Legal", icon: FileSignature },
  { title: "Billing", icon: CreditCard },
  { title: "Demo", icon: Upload },
];

function StepAccount() {
  const { companyName, legalEmail, setCompanyName, setLegalEmail } = useOnboardingStore();

  return (
    <div className="space-y-4">
      <h2 className="font-heading text-app-2xl font-bold">Create your account</h2>
      <p className="text-app-base text-muted-foreground">We will send a magic link for secure sign-in.</p>
      <label className="block space-y-1">
        <span className="text-app-sm font-medium text-foreground">Company Name</span>
        <input
          value={companyName}
          onChange={(event) => setCompanyName(event.target.value)}
          className="h-10 w-full rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
          placeholder="Acme Brands Inc."
        />
      </label>
      <label className="block space-y-1">
        <span className="text-app-sm font-medium text-foreground">Legal Contact Email</span>
        <input
          value={legalEmail}
          onChange={(event) => setLegalEmail(event.target.value)}
          className="h-10 w-full rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
          placeholder="legal@acme.com"
        />
      </label>
    </div>
  );
}

function StepLegal() {
  const { loaSigned, setLoaSigned } = useOnboardingStore();

  return (
    <div className="space-y-4">
      <h2 className="font-heading text-app-2xl font-bold">Sign LOA</h2>
      <p className="text-app-base text-muted-foreground">
        Digitally authorize SniperIP to enforce notices on your behalf.
      </p>
      <div className="rounded-md border bg-muted p-4">
        <div className="h-56 rounded-sm border bg-white p-3 text-app-sm text-muted-foreground">
          DocuSign embed placeholder
        </div>
      </div>
      <button
        type="button"
        onClick={() => setLoaSigned(true)}
        className="inline-flex items-center gap-2 rounded-md bg-sniper-charcoal px-4 py-2 text-app-sm font-semibold text-white"
      >
        {loaSigned ? <CheckCircle2 className="h-4 w-4 text-sniper-green" /> : null}
        {loaSigned ? "LOA Signed" : "Mark as Signed"}
      </button>
    </div>
  );
}

function StepBilling() {
  const { billingComplete, setBillingComplete } = useOnboardingStore();
  const [selected, setSelected] = useState("GROWTH");
  const [redirecting, setRedirecting] = useState(false);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  const plans = [
    { name: "Starter", tier: "STARTER", price: "$99/mo" },
    { name: "Growth", tier: "GROWTH", price: "$500/mo" },
    { name: "Agency", tier: "AGENCY", price: "$1,500/mo", contactSales: true },
  ];

  async function handleCheckout() {
    const plan = plans.find((p) => p.tier === selected);
    if (!plan) return;
    if (plan.contactSales) {
      window.location.href = "mailto:sales@sniperip.com?subject=Agency Plan Inquiry";
      return;
    }
    setRedirecting(true);
    setCheckoutError(null);
    try {
      const url = await createCheckoutSession(
        plan.tier,
        `${window.location.origin}/dashboard?onboarding=complete`,
        `${window.location.origin}/onboarding`,
      );
      setBillingComplete(true);
      window.location.href = url;
    } catch {
      setCheckoutError("Could not start checkout. Please try again.");
      setRedirecting(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="font-heading text-app-2xl font-bold">Billing Setup</h2>
      <p className="text-app-base text-muted-foreground">Select a plan to open Stripe Checkout.</p>
      <div className="grid grid-cols-1 gap-2">
        {plans.map((plan) => (
          <button
            key={plan.name}
            type="button"
            onClick={() => setSelected(plan.tier)}
            className={`rounded-md border px-3 py-3 text-left ${selected === plan.tier ? "border-2 border-sniper-green" : "bg-white"}`}
          >
            <p className="font-heading text-app-lg font-semibold">{plan.name}</p>
            <p className="text-app-sm text-muted-foreground">{plan.price}</p>
          </button>
        ))}
      </div>
      {checkoutError ? (
        <p className="text-app-sm text-red-600">{checkoutError}</p>
      ) : null}
      {billingComplete ? (
        <div className="rounded-md border border-sniper-green bg-sniper-green-muted p-3 text-app-sm text-sniper-charcoal">
          Redirecting to Stripe…
        </div>
      ) : (
        <button
          type="button"
          disabled={redirecting}
          onClick={handleCheckout}
          className="inline-flex items-center gap-2 rounded-md bg-sniper-charcoal px-4 py-2 text-app-sm font-semibold text-white disabled:opacity-60"
        >
          <CreditCard className="h-4 w-4" />
          {redirecting ? "Redirecting…" : "Continue to Payment"}
        </button>
      )}
    </div>
  );
}

function StepDemo({ activated, onActivate }: { activated: boolean; onActivate: () => void }) {
  const status = activated ? "APPROVED" : "PENDING_APPROVAL";

  return (
    <div className="space-y-4">
      <h2 className="font-heading text-app-2xl font-bold">Demo Mode</h2>
      <p className="text-app-base text-muted-foreground">Approve one threat to unlock your dashboard.</p>
      <div className="rounded-md border bg-white p-3">
        <div className="mb-2 flex items-center justify-between border-b pb-2">
          <p className="text-app-sm font-medium">counterfeit-mall.example.com</p>
          <span className={`rounded-sm px-2 py-1 text-app-xs ${activated ? "bg-[#D4EDDA] text-[#155724]" : "bg-[#FFF3CD] text-[#856404]"}`}>
            {status}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <p className="text-app-xs text-muted-foreground">Similarity 97%</p>
          <button
            type="button"
            onClick={onActivate}
            className="relative inline-flex items-center gap-2 rounded-md bg-sniper-green px-3 py-1.5 text-app-xs font-semibold text-sniper-charcoal"
          >
            Approve
            <SniperChevron className={`h-3 w-3 ${activated ? "scale-110" : "animate-pulse-green"}`} />
          </button>
        </div>
      </div>
      {activated ? (
        <p className="text-app-sm font-medium text-[#0A7C2E]">Takedown Filed!</p>
      ) : (
        <p className="text-app-xs text-muted-foreground">Try approving this threat to continue.</p>
      )}
    </div>
  );
}

export default function OnboardingPage() {
  const { step, totalSteps, nextStep, prevStep } = useOnboardingStore();
  const [demoActivated, setDemoActivated] = useState(false);

  const content = [
    <StepAccount key="account" />,
    <StepLegal key="legal" />,
    <StepBilling key="billing" />,
    <StepDemo key="demo" activated={demoActivated} onActivate={() => setDemoActivated(true)} />,
  ][step - 1];

  const canFinish = step < totalSteps || demoActivated;

  return (
    <div className="min-h-screen bg-white px-4 py-10">
      <div className="mx-auto w-full max-w-[560px]">
        <div className="mb-8 flex flex-col items-center gap-4 text-center">
          <Image src="/logo-dark.png" alt="SniperIP" width={220} height={220} className="h-14 w-auto" />
          <div className="flex w-full items-center justify-center gap-2">
            {steps.map((item, index) => {
              const current = index + 1 === step;
              const complete = index + 1 < step;

              return (
                <div key={item.title} className="flex items-center gap-2">
                  <span
                    className={`h-2.5 w-2.5 rounded-full border ${
                      complete ? "border-sniper-charcoal bg-sniper-charcoal" : current ? "border-sniper-green bg-sniper-green" : "border-[#8E95A3]"
                    }`}
                  />
                  {index < steps.length - 1 ? <span className="h-px w-8 bg-border" /> : null}
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-md border bg-white p-6 shadow-sniper-lg">
          {content}
        </div>

        <div className="mt-4 flex items-center justify-between">
          {step > 1 ? (
            <button
              type="button"
              onClick={prevStep}
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-app-sm font-medium"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          ) : (
            <Link href="/" className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-app-sm font-medium">
              <ArrowLeft className="h-4 w-4" />
              Home
            </Link>
          )}

          {step < totalSteps ? (
            <button
              type="button"
              onClick={nextStep}
              className="inline-flex items-center gap-2 rounded-md bg-sniper-charcoal px-4 py-2 text-app-sm font-semibold text-white"
            >
              Continue
              <ArrowRight className="h-4 w-4" />
            </button>
          ) : (
            <Link
              href="/dashboard"
              className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-app-sm font-semibold ${
                canFinish ? "bg-sniper-green text-sniper-charcoal" : "cursor-not-allowed bg-muted text-muted-foreground"
              }`}
              onClick={(event) => {
                if (!canFinish) {
                  event.preventDefault();
                }
              }}
            >
              Go to Dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
