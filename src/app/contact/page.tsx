import Link from "next/link";
import { LegalShell } from "@/components/marketing/legal-shell";

export default function ContactPage() {
  return (
    <LegalShell
      title="Contact"
      description="Need onboarding help, legal support, or enterprise pricing?"
    >
      <p>
        Email:{" "}
        <a className="text-emerald-300 hover:text-emerald-200" href="mailto:hello@sniperip.com">
          hello@sniperip.com
        </a>
      </p>
      <p>
        Support hours: Monday to Friday, 9:00 AM to 6:00 PM Pacific Time.
      </p>
      <p>
        Existing clients can also use the dashboard for threat-level escalation
        and dead-letter queue incidents.
      </p>
      <p>
        Ready to start now?{" "}
        <Link href="/auth/login" className="text-emerald-300 hover:text-emerald-200">
          Launch free scan
        </Link>
        .
      </p>
    </LegalShell>
  );
}
