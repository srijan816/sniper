import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Legal Escalation Partners | SniperIP",
  description:
    "Connect with specialist IP law firms for counter-notice litigation and advanced brand enforcement.",
};

type Firm = {
  name: string;
  specialization: string;
  coverage: string;
  description: string;
  mailtoSubject: string;
};

const firms: Firm[] = [
  {
    name: "IP Guardian Law Group",
    specialization: "E-commerce & DTC Brand Protection",
    coverage: "US, EU, UK",
    description:
      "Specialists in DMCA counter-notice litigation and marketplace enforcement. Offers fixed-fee packages for initial consultations.",
    mailtoSubject: "SniperIP Referral — Counter-Notice Litigation Inquiry",
  },
  {
    name: "Digital Rights Advocates",
    specialization: "Copyright & Counterfeit Litigation",
    coverage: "US, Canada",
    description:
      "Boutique IP firm with deep experience in cross-border counterfeit enforcement and Amazon Brand Registry disputes.",
    mailtoSubject: "SniperIP Referral — Counterfeit Enforcement Inquiry",
  },
  {
    name: "Commerce Shield Legal",
    specialization: "Trademark & Trade Dress",
    coverage: "Global",
    description:
      "Full-service IP boutique representing DTC brands in platform disputes, federal litigation, and international enforcement.",
    mailtoSubject: "SniperIP Referral — Trademark & Trade Dress Inquiry",
  },
];

export default function LegalPartnersPage() {
  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-app-2xl font-bold">Legal Escalation Partners</h1>
        <p className="max-w-2xl text-app-base text-muted-foreground">
          When automated takedowns are challenged or a platform restores an infringing listing,
          you may need specialist IP legal counsel. The firms below work with e-commerce and DTC
          brands on counter-notice responses, federal litigation, and cross-border enforcement.
        </p>
      </header>

      <section className="rounded-md border border-amber-200 bg-amber-50 p-5">
        <h2 className="font-heading text-app-base font-semibold text-amber-900">
          Understanding Counter-Notices
        </h2>
        <p className="mt-2 text-app-sm text-amber-800">
          A counter-notice is a legal document that a seller can file with a platform after their
          listing is removed via a DMCA takedown. If the counter-notice is valid, platforms are
          legally required to restore the content within 10-14 business days — unless you file a
          federal lawsuit within that window. Counter-notices also shift perjury liability to the
          filer if their claim is false. If SniperIP has flagged a reinstated listing or you have
          received notice of a counter-claim, engaging an IP attorney promptly is strongly advised.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {firms.map((firm) => {
          const mailtoHref = `mailto:?subject=${encodeURIComponent(firm.mailtoSubject)}&body=${encodeURIComponent(
            `Hi,\n\nI was referred by SniperIP and would like to discuss a brand enforcement matter with ${firm.name}.\n\nPlease reach out at your earliest convenience.\n\nThank you.`,
          )}`;

          return (
            <article
              key={firm.name}
              className="flex flex-col rounded-md border bg-card p-6 shadow-sniper-sm"
            >
              <div className="flex-1 space-y-3">
                <div className="space-y-1">
                  <h3 className="font-heading text-app-xl font-bold text-foreground">
                    {firm.name}
                  </h3>
                  <span className="inline-block rounded-full border border-sniper-green/40 bg-sniper-green-muted px-2.5 py-0.5 text-app-xs font-medium text-sniper-charcoal">
                    {firm.specialization}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-app-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Coverage
                  </span>
                  <span className="text-app-sm text-foreground">{firm.coverage}</span>
                </div>

                <p className="text-app-sm leading-relaxed text-muted-foreground">
                  {firm.description}
                </p>
              </div>

              <div className="mt-5 pt-4 border-t">
                <a
                  href={mailtoHref}
                  className="inline-flex w-full items-center justify-center rounded-md border border-sniper-charcoal bg-white px-4 py-2.5 font-heading text-app-sm font-semibold text-sniper-charcoal transition hover:bg-sniper-charcoal hover:text-white"
                >
                  Contact for Escalation
                </a>
              </div>
            </article>
          );
        })}
      </section>

      <footer className="rounded-md border bg-muted/40 px-5 py-4">
        <p className="text-app-xs text-muted-foreground">
          <strong>Disclosure:</strong> SniperIP may receive a referral fee when clients engage
          these legal partners. This does not affect our platform&apos;s enforcement decisions.
        </p>
      </footer>
    </div>
  );
}
