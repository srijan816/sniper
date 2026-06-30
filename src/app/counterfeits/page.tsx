import { SiteHeader } from "@/components/marketing/site-header";
import { SiteFooter } from "@/components/marketing/site-footer";

export const dynamic = "force-dynamic";

type Counterfeit = {
  id: string;
  original_image: string | null;
  infringing_image: string | null;
  listing_url: string | null;
  marketplace: string | null;
  seller: string | null;
  title: string | null;
  similarity: number | null;
  status: string | null;
  detected_at: string | null;
};

async function getCounterfeits(): Promise<{ items: Counterfeit[]; disclaimer: string }> {
  const internal = process.env.BACKEND_URL ? `${process.env.BACKEND_URL}/api` : "";
  const base = internal || process.env.NEXT_PUBLIC_BACKEND_URL || "";
  try {
    const res = await fetch(`${base}/counterfeits?limit=60`, { cache: "no-store" });
    if (!res.ok) return { items: [], disclaimer: "" };
    const json = await res.json();
    return { items: json.data ?? [], disclaimer: json.meta?.disclaimer ?? "" };
  } catch {
    return { items: [], disclaimer: "" };
  }
}

function pct(v: number | null): string {
  if (v == null) return "—";
  return `${Math.round((v <= 1 ? v * 100 : v))}%`;
}

export default async function CounterfeitsPage() {
  const { items, disclaimer } = await getCounterfeits();
  return (
    <div className="min-h-screen bg-white text-[#1A1C24]">
      <SiteHeader />
      <main className="mx-auto w-full max-w-7xl px-6 py-14">
        <section className="mb-8 text-center">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[#475569]">
            Enforcement wall
          </span>
          <h1 className="mt-2 font-[family-name:var(--font-heading)] text-4xl font-extrabold tracking-tight leading-snug md:text-5xl">
            Suspected counterfeit matches
          </h1>
          <p className="mx-auto mt-4 max-w-3xl text-lg text-[#475569]">
            Reviewed image-similarity matches between a brand&rsquo;s protected
            product photo and a marketplace listing.
          </p>
          <p className="mx-auto mt-3 max-w-3xl rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {disclaimer ||
              "Similarity is an automated indicator, not a legal determination. Listings shown have been human-reviewed."}
          </p>
        </section>

        {items.length === 0 ? (
          <div className="rounded-md border border-[#E2E8F0] bg-[#F8F9FA] p-12 text-center">
            <p className="text-lg font-semibold">No verified matches to show yet.</p>
            <p className="mx-auto mt-2 max-w-xl text-sm text-[#475569]">
              Confirmed image-similarity matches appear here after review. The
              detection engine (SigLIP&nbsp;+&nbsp;DINOv2&nbsp;+&nbsp;pHash) flags
              listings that reuse a protected product photo.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((c) => (
              <article key={c.id} className="overflow-hidden rounded-md border border-[#E2E8F0] bg-white shadow-sm">
                <div className="grid grid-cols-2">
                  <figure className="border-r border-[#E2E8F0]">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={c.original_image ?? ""} alt="Protected original" referrerPolicy="no-referrer"
                         className="aspect-square w-full object-cover" />
                    <figcaption className="bg-[#F0FDF4] px-2 py-1 text-center text-[11px] font-semibold text-green-800">ORIGINAL</figcaption>
                  </figure>
                  <figure>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={c.infringing_image ?? ""} alt="Suspected listing" referrerPolicy="no-referrer"
                         className="aspect-square w-full object-cover" />
                    <figcaption className="bg-[#FEF2F2] px-2 py-1 text-center text-[11px] font-semibold text-red-800">SUSPECTED LISTING</figcaption>
                  </figure>
                </div>
                <div className="space-y-1 p-4">
                  <div className="flex items-center justify-between">
                    <span className="rounded bg-[#1A1C24] px-2 py-0.5 text-xs font-bold text-white">{pct(c.similarity)} match</span>
                    <span className="text-xs font-medium text-[#475569]">{c.status}</span>
                  </div>
                  <p className="truncate text-sm font-semibold" title={c.title ?? ""}>{c.title ?? "Listing"}</p>
                  <p className="text-xs text-[#475569]">{c.marketplace}{c.seller ? ` · ${c.seller}` : ""}</p>
                  {c.listing_url && (
                    <a href={c.listing_url} target="_blank" rel="noreferrer nofollow"
                       className="inline-block pt-1 text-xs font-semibold text-blue-700 underline">View listing →</a>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
      <SiteFooter />
    </div>
  );
}
