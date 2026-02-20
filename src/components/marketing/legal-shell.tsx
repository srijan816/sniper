import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";

export function LegalShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-white text-[#1A1C24]">
      <SiteHeader />
      <main className="mx-auto w-full max-w-4xl px-6 py-16">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-md border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-[#475569] hover:border-[#1A1C24] hover:text-[#1A1C24]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Home
        </Link>

        <section className="mt-8 rounded-md border border-[#E2E8F0] bg-white p-6 shadow-[0_4px_6px_-1px_rgba(26,28,36,0.08),0_2px_4px_-1px_rgba(26,28,36,0.04)] md:p-8">
          <h1 className="font-[family-name:var(--font-heading)] text-4xl font-extrabold tracking-tight">
            {title}
          </h1>
          <p className="mt-3 text-[#475569]">{description}</p>
          <div className="mt-8 space-y-4 text-sm leading-relaxed text-[#475569]">
            {children}
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
