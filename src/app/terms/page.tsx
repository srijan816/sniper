import { LegalShell } from "@/components/marketing/legal-shell";

export default function TermsPage() {
  return (
    <LegalShell
      title="Terms of Service"
      description="These terms govern access to SniperIP's marketing site, dashboard, and automated takedown tooling."
    >
      <p>
        SniperIP provides software automation for counterfeit discovery and
        takedown workflow management. You are responsible for the legal accuracy
        of your submissions and all account activity.
      </p>
      <p>
        Use of the service requires a valid Letter of Authorization (LOA) and
        compliance with platform abuse policies. We reserve the right to suspend
        misuse, fraudulent activity, or non-payment.
      </p>
      <p>
        Subscription billing, renewals, and cancellations are processed through
        Stripe. By subscribing, you authorize recurring charges for your plan
        tier until canceled.
      </p>
    </LegalShell>
  );
}
