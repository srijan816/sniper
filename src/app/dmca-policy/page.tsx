import { LegalShell } from "@/components/marketing/legal-shell";

export default function DmcaPolicyPage() {
  return (
    <LegalShell
      title="DMCA Policy"
      description="SniperIP supports rights holders by automating notice workflows with client authorization."
    >
      <p>
        DMCA submissions are initiated only after client approval within the
        SniperIP dashboard or through pre-authorized automation settings.
      </p>
      <p>
        Each status transition is recorded in immutable audit logs to provide an
        evidence trail for authorization and submission timing.
      </p>
      <p>
        If you believe a takedown was sent in error, contact our team using the
        contact details below and include case identifiers for expedited review.
      </p>
    </LegalShell>
  );
}
