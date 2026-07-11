"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";

type Stage = "boot" | "ready";

export default function UnderConstructionPage() {
  const [stage, setStage] = useState<Stage>("boot");
  const [videoReady, setVideoReady] = useState(false);

  useEffect(() => {
    // Paint solid shell first, then reveal content after the first frame
    // so we never flash light theme / stacked poster text.
    const id = window.requestAnimationFrame(() => setStage("ready"));
    return () => window.cancelAnimationFrame(id);
  }, []);

  const markVideoReady = useCallback(() => {
    setVideoReady(true);
  }, []);

  return (
    <div className="relative min-h-dvh overflow-hidden bg-[#05070a] text-white">
      {/* Instant text-free still so first paint matches the final look */}
      <div
        className="absolute inset-0 bg-[#05070a] bg-cover bg-center"
        style={{ backgroundImage: "url(/under-construction/bg-still.jpg)" }}
        aria-hidden
      />

      {/* Video fades in over the still once it can play — never carries text */}
      <video
        className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-1000 ease-out ${
          videoReady ? "opacity-100" : "opacity-0"
        }`}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        onCanPlay={markVideoReady}
        onLoadedData={markVideoReady}
        onPlaying={markVideoReady}
        aria-hidden
      >
        <source src="/under-construction/bg.mp4" type="video/mp4" />
      </video>

      {/* Atmospheric overlays — always present, same final look from frame 1 */}
      <div
        className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/55 via-black/35 to-black/70"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(5,7,10,0.55)_70%,rgba(5,7,10,0.9)_100%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -top-1/4 left-1/2 h-[60vh] w-[80vw] -translate-x-1/2 rounded-full bg-emerald-500/10 blur-3xl"
        aria-hidden
      />

      {/* Single source of truth for copy — only HTML, never baked into poster */}
      <main
        className={`relative z-10 flex min-h-dvh flex-col items-center justify-center px-6 text-center transition-all duration-700 ease-out ${
          stage === "ready"
            ? "translate-y-0 opacity-100"
            : "translate-y-2 opacity-0"
        }`}
      >
        <div className="mb-10 opacity-95">
          <Image
            src="/logo-light.png"
            alt="SniperIP"
            width={160}
            height={160}
            className="mx-auto h-12 w-auto sm:h-14"
            priority
          />
        </div>

        <p className="mb-4 text-[11px] font-medium uppercase tracking-[0.35em] text-emerald-400/90">
          We&apos;ll be right back
        </p>

        <h1 className="font-[family-name:var(--font-heading)] text-4xl font-extrabold tracking-tight text-white drop-shadow-[0_0_40px_rgba(16,217,75,0.18)] sm:text-5xl md:text-6xl lg:text-7xl">
          Site Under Construction
        </h1>

        <div className="mt-6 flex items-center gap-3" aria-hidden>
          <span className="h-px w-10 bg-gradient-to-r from-transparent to-emerald-400/80" />
          <span className="inline-block h-2 w-2 rotate-45 border border-emerald-400/90 shadow-[0_0_12px_rgba(16,217,75,0.7)]" />
          <span className="h-px w-10 bg-gradient-to-l from-transparent to-emerald-400/80" />
        </div>

        <p className="mt-8 max-w-md text-base leading-relaxed text-white/70 sm:text-lg">
          SniperIP is getting a fresh build. Something sharper is on the way.
        </p>

        <a
          href="mailto:hello@sniperip.com"
          className="mt-10 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-medium text-white/90 backdrop-blur-md transition hover:border-emerald-400/50 hover:bg-emerald-400/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#05070a]"
        >
          hello@sniperip.com
        </a>
      </main>
    </div>
  );
}
