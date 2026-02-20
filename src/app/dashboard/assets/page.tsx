"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { ArrowRight, ImageIcon, Upload, Video } from "lucide-react";

type Asset = {
  id: string;
  name: string;
  type: "IMAGE" | "VIDEO";
  createdAt: string;
  threats: number;
};

const initialAssets: Asset[] = [
  {
    id: "asset_01",
    name: "hero-sneaker-front.jpg",
    type: "IMAGE",
    createdAt: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(),
    threats: 12,
  },
  {
    id: "asset_02",
    name: "matte-bottle-hero.png",
    type: "IMAGE",
    createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    threats: 5,
  },
  {
    id: "asset_03",
    name: "product-spin.mp4",
    type: "VIDEO",
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    threats: 2,
  },
];

export default function AssetsPage() {
  const [dragOver, setDragOver] = useState(false);
  const [assets] = useState(initialAssets);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Assets</h1>
        <p className="text-app-base text-muted-foreground">
          Upload and manage product visuals used by the radar and enforcement pipeline.
        </p>
      </header>

      <section
        onDragOver={(event) => {
          event.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragOver(false);
        }}
        className={`rounded-md border-2 border-dashed p-8 text-center transition ${
          dragOver ? "border-sniper-green bg-sniper-green-muted" : "border-[#8E95A3] bg-white"
        }`}
      >
        <Upload className="mx-auto h-7 w-7 text-muted-foreground" />
        <p className="mt-3 text-app-base text-muted-foreground">Drag & drop product images or video</p>
        <button type="button" className="mt-1 text-app-sm font-medium text-[#0A7C2E] underline">
          Browse Files
        </button>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {assets.map((asset) => {
          const Icon = asset.type === "VIDEO" ? Video : ImageIcon;
          return (
            <article key={asset.id} className="overflow-hidden rounded-md border bg-white shadow-sniper-sm">
              <div className="relative aspect-video border-b bg-muted">
                <Image
                  src={asset.type === "VIDEO" ? "/threat-inbox-demo.webp" : "/hero-dashboard.webp"}
                  alt={asset.name}
                  fill
                  className="object-cover"
                />
              </div>
              <div className="space-y-3 p-4">
                <div>
                  <p className="truncate font-heading text-app-lg font-semibold text-foreground">{asset.name}</p>
                  <div className="mt-1 inline-flex items-center gap-1 rounded-sm bg-muted px-2 py-1 text-app-xs font-medium text-muted-foreground">
                    <Icon className="h-3.5 w-3.5" />
                    {asset.type}
                  </div>
                </div>
                <p className="text-app-xs text-muted-foreground">
                  Added {new Date(asset.createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                </p>
                <Link
                  href={`/dashboard/threats?asset=${asset.id}`}
                  className="inline-flex items-center gap-1 text-app-sm font-medium text-foreground hover:underline"
                >
                  <span className="text-[#0A7C2E] font-semibold">{asset.threats} active threats</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
}
