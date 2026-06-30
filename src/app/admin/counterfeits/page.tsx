"use client";

import { useEffect, useState } from "react";
import { getCounterfeits, type Counterfeit } from "@/lib/api";

function pct(v: number | null): string {
  if (v == null) return "—";
  return `${Math.round(v <= 1 ? v * 100 : v)}%`;
}

export default function AdminCounterfeitsPage() {
  const [items, setItems] = useState<Counterfeit[]>([]);
  const [disclaimer, setDisclaimer] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCounterfeits()
      .then((r) => {
        setItems(r.data ?? []);
        setDisclaimer(r.meta?.disclaimer ?? "");
      })
      .catch(() => setError("Failed to load — are you signed in as an admin?"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Suspected Counterfeits</h1>
        <p className="text-app-base text-muted-foreground">
          Human-reviewed image-similarity matches between a protected product photo and a marketplace listing.
        </p>
      </header>

      <p className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-app-sm text-amber-900">
        {disclaimer ||
          "Similarity is an automated indicator, not a legal determination. Only human-reviewed matches are shown."}
      </p>

      {error ? (
        <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p>
      ) : loading ? (
        <p className="text-app-sm text-muted-foreground">Loading…</p>
      ) : items.length === 0 ? (
        <div className="rounded-md border border-[#E2E8F0] bg-[#F8F9FA] p-12 text-center">
          <p className="text-app-base font-semibold">No verified matches yet.</p>
          <p className="mx-auto mt-2 max-w-xl text-app-sm text-muted-foreground">
            Reviewed matches appear here. The detection engine (SigLIP&nbsp;+&nbsp;DINOv2&nbsp;+&nbsp;pHash)
            flags listings that reuse a protected product photo.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((c) => (
            <article key={c.id} className="overflow-hidden rounded-md border border-[#E2E8F0] bg-white shadow-sm">
              <div className="grid grid-cols-2">
                <figure className="border-r border-[#E2E8F0]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={c.original_image ?? ""} alt="Protected original" referrerPolicy="no-referrer" className="aspect-square w-full object-cover" />
                  <figcaption className="bg-[#F0FDF4] px-2 py-1 text-center text-[11px] font-semibold text-green-800">ORIGINAL</figcaption>
                </figure>
                <figure>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={c.infringing_image ?? ""} alt="Suspected listing" referrerPolicy="no-referrer" className="aspect-square w-full object-cover" />
                  <figcaption className="bg-[#FEF2F2] px-2 py-1 text-center text-[11px] font-semibold text-red-800">SUSPECTED LISTING</figcaption>
                </figure>
              </div>
              <div className="space-y-1 p-4">
                <div className="flex items-center justify-between">
                  <span className="rounded bg-[#1A1C24] px-2 py-0.5 text-xs font-bold text-white">{pct(c.similarity)} match</span>
                  <span className="text-xs font-medium text-muted-foreground">{c.status}</span>
                </div>
                <p className="truncate text-app-sm font-semibold" title={c.title ?? ""}>{c.title ?? "Listing"}</p>
                <p className="text-xs text-muted-foreground">{c.marketplace}{c.seller ? ` · ${c.seller}` : ""}</p>
                {c.listing_url && (
                  <a href={c.listing_url} target="_blank" rel="noreferrer nofollow" className="inline-block pt-1 text-xs font-semibold text-blue-700 underline">View listing →</a>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
