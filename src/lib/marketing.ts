import type { LucideIcon } from "lucide-react";
import {
  Bot,
  Crosshair,
  Radar,
  Scale,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";

export type PricingTier = {
  name: string;
  price: string;
  period?: string;
  description: string;
  features: string[];
  cta: string;
  checkoutHref: string;
  featured?: boolean;
  badge?: string;
};

export type WorkflowStep = {
  title: string;
  description: string;
  icon: LucideIcon;
};

export type MoatCard = {
  title: string;
  description: string;
  icon: LucideIcon;
};

export const pricingTiers: PricingTier[] = [
  {
    name: "Starter",
    price: "$99",
    period: "/mo",
    description: "3 assets. 50 enforcements per month. Daily monitoring.",
    features: [
      "3 Assets",
      "50 Enforcements/mo",
      "Daily Scans",
      "Threat Inbox + CSV Export",
    ],
    cta: "Choose Starter",
    checkoutHref: "/onboarding?plan=starter",
  },
  {
    name: "Growth",
    price: "$500",
    period: "/mo",
    description: "Unlimited assets. 500 enforcements. Automated approvals.",
    features: [
      "Unlimited Assets",
      "500 Enforcements/mo",
      "Automated Approvals",
      "Priority Support",
    ],
    cta: "Choose Growth",
    checkoutHref: "/onboarding?plan=growth",
    featured: true,
    badge: "Most Popular",
  },
  {
    name: "Agency",
    price: "$1,500",
    period: "/mo",
    description: "Multi-brand support. 5,000 enforcements. API access.",
    features: [
      "Multi-Brand Support",
      "5,000 Enforcements/mo",
      "White-Labeled Reports",
      "API Access",
    ],
    cta: "Contact Sales",
    checkoutHref: "/contact",
  },
];

export const workflowSteps: WorkflowStep[] = [
  {
    title: "Ingest & Vectorize",
    description:
      "Upload product photos or videos. Vision AI maps the semantic DNA of your IP.",
    icon: Upload,
  },
  {
    title: "Continuous Radar",
    description:
      "We scan Google Lens, AliExpress, and Shopify footprints 24/7 to detect clones.",
    icon: Radar,
  },
  {
    title: "One-Click Enforce",
    description:
      "Approve threats in your dashboard and automation submits compliant claims.",
    icon: Crosshair,
  },
];

export const moatCards: MoatCard[] = [
  {
    title: "SigLIP 2 Vision AI",
    description:
      "Finds fakes even when infringers crop, watermark, or alter your product photos.",
    icon: Sparkles,
  },
  {
    title: "512(f) Legal Compliance",
    description:
      "DocuSign LOA + immutable approval logs reduce false-claim liability risk.",
    icon: Scale,
  },
  {
    title: "Playwright RPA",
    description:
      "Automation workers handle repetitive abuse-form filing at platform speed.",
    icon: Bot,
  },
  {
    title: "False-Positive Shield",
    description:
      "Whitelist controls protect authorized resellers and wholesale channels.",
    icon: ShieldCheck,
  },
];
