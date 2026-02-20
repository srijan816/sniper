import { LegalShell } from "@/components/marketing/legal-shell";

export default function PrivacyPage() {
  return (
    <LegalShell
      title="Privacy Policy"
      description="This policy explains what data SniperIP collects and how it is processed."
    >
      <p>
        We collect account information, uploaded brand assets, threat records,
        and workflow metadata required to operate the service.
      </p>
      <p>
        Data is processed to discover infringements, generate verification
        signals, and execute approved takedown actions. We retain immutable
        audit logs for legal compliance and security monitoring.
      </p>
      <p>
        Payment details are handled by Stripe. We do not store full card
        numbers. You may request account deletion according to legal retention
        constraints for active disputes and compliance records.
      </p>
    </LegalShell>
  );
}
