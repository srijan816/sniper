"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, ImageIcon, Upload, Video } from "lucide-react";
import { listAssets, listThreats, uploadAsset, type Asset, type Threat } from "@/lib/api";

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function AssetsPage() {
  const [dragOver, setDragOver] = useState(false);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [threats, setThreats] = useState<Threat[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [assetList, threatList] = await Promise.all([listAssets(), listThreats()]);
      setAssets(assetList.filter((asset) => asset.status !== "ARCHIVED"));
      setThreats(threatList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load assets.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const activeThreatsByAsset = useMemo(() => {
    const map = new Map<string, number>();
    threats.forEach((threat) => {
      if (threat.status === "REMOVED" || threat.status === "WHITELISTED" || threat.status === "REJECTED") {
        return;
      }
      map.set(threat.asset_id, (map.get(threat.asset_id) ?? 0) + 1);
    });
    return map;
  }, [threats]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    try {
      setUploading(true);
      setError(null);
      for (const file of Array.from(files)) {
        const type = file.type.startsWith("video/") ? "VIDEO" : "IMAGE";
        await uploadAsset(file, type);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Assets</h1>
        <p className="text-app-base text-muted-foreground">Upload and manage product visuals used by the radar and enforcement pipeline.</p>
      </header>

      {error ? (
        <section className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-app-sm text-destructive">{error}</section>
      ) : null}

      <section
        onDragOver={(event) => {
          event.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragOver(false);
          void handleFiles(event.dataTransfer.files);
        }}
        className={`rounded-md border-2 border-dashed p-8 text-center transition ${
          dragOver ? "border-sniper-green bg-sniper-green-muted" : "border-[#8E95A3] bg-white"
        }`}
      >
        <Upload className="mx-auto h-7 w-7 text-muted-foreground" />
        <p className="mt-3 text-app-base text-muted-foreground">Drag and drop product images or video</p>
        <button type="button" onClick={() => fileInputRef.current?.click()} className="mt-1 text-app-sm font-medium text-[#0A7C2E] underline">
          {uploading ? "Uploading..." : "Browse Files"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,video/*"
          className="hidden"
          onChange={(event) => void handleFiles(event.target.files)}
        />
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {!loading && assets.length === 0 ? (
          <article className="col-span-full rounded-md border bg-white p-8 text-center text-app-sm text-muted-foreground shadow-sniper-sm">
            No assets uploaded yet.
          </article>
        ) : null}
        {assets.map((asset) => {
          const Icon = asset.asset_type === "VIDEO" ? Video : ImageIcon;
          const preview = asset.thumbnail_url || asset.storage_url || "/hero-dashboard.webp";
          const activeThreats = activeThreatsByAsset.get(asset.id) ?? 0;
          return (
            <article key={asset.id} className="overflow-hidden rounded-md border bg-white shadow-sniper-sm">
              <div className="relative aspect-video border-b bg-muted">
                <img src={preview} alt={asset.original_filename} className="h-full w-full object-cover" />
              </div>
              <div className="space-y-3 p-4">
                <div>
                  <p className="truncate font-heading text-app-lg font-semibold text-foreground">{asset.original_filename}</p>
                  <div className="mt-1 inline-flex items-center gap-1 rounded-sm bg-muted px-2 py-1 text-app-xs font-medium text-muted-foreground">
                    <Icon className="h-3.5 w-3.5" />
                    {asset.asset_type}
                  </div>
                </div>
                <p className="text-app-xs text-muted-foreground">Added {formatDate(asset.created_at)}</p>
                <Link href={`/dashboard/threats?asset=${asset.id}`} className="inline-flex items-center gap-1 text-app-sm font-medium text-foreground hover:underline">
                  <span className="font-semibold text-[#0A7C2E]">{activeThreats} active threats</span>
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
