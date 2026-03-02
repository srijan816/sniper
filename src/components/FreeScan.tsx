"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ScanResult = {
  platform: string;
  country: string;
  similarity_score: number;
  thumbnail_url: string | null;
  domain_hint: string;
};

type ScanResponse = {
  total_matches_found: number;
  high_confidence_matches: number;
  results: ScanResult[];
  cta_message: string;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const COUNTDOWN_START = 20;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function FreeScan() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [countdown, setCountdown] = useState(COUNTDOWN_START);
  const [response, setResponse] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (countdownRef.current !== null) {
        clearInterval(countdownRef.current);
      }
    };
  }, []);

  // ---------------------------------------------------------------------------
  // File handling
  // ---------------------------------------------------------------------------

  const handleFile = useCallback((f: File) => {
    if (!f.type.startsWith("image/")) {
      setError("Please upload an image file (JPG, PNG, WEBP, etc.).");
      return;
    }
    setError(null);
    setFile(f);
    setResponse(null);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(f);
  }, []);

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => setIsDragging(false);

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };

  // ---------------------------------------------------------------------------
  // Submission
  // ---------------------------------------------------------------------------

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError("Please upload a product image before scanning.");
      return;
    }
    if (!email.trim()) {
      setError("Please enter your email address.");
      return;
    }

    setError(null);
    setResponse(null);
    setIsLoading(true);
    setCountdown(COUNTDOWN_START);

    // Start countdown timer
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          if (countdownRef.current !== null) {
            clearInterval(countdownRef.current);
            countdownRef.current = null;
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("email", email.trim());

      const res = await fetch(`${BACKEND_URL}/api/scan/free`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        let detail = `Request failed with status ${res.status}.`;
        try {
          const body = await res.json();
          if (body?.detail) detail = body.detail;
        } catch {
          // ignore JSON parse errors
        }
        if (res.status === 429) {
          detail =
            "You have reached the free scan limit (3 per day). Sign up to run unlimited scans.";
        }
        throw new Error(detail);
      }

      const data: ScanResponse = await res.json();
      setResponse(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      if (countdownRef.current !== null) {
        clearInterval(countdownRef.current);
        countdownRef.current = null;
      }
      setIsLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  const renderThumbnail = (result: ScanResult) => {
    if (result.thumbnail_url && result.thumbnail_url.startsWith("data:")) {
      return (
        <img
          src={result.thumbnail_url}
          alt="Blurred product thumbnail"
          className="h-full w-full object-cover"
        />
      );
    }
    return (
      <div className="flex h-full w-full items-center justify-center bg-[#E2E8F0]">
        <span className="text-xs text-[#475569]">No preview</span>
      </div>
    );
  };

  const similarityPercent = (score: number) =>
    `${Math.round(score * 100)}%`;

  const similarityColor = (score: number) => {
    if (score >= 0.8) return "text-red-500";
    if (score >= 0.65) return "text-orange-500";
    return "text-yellow-500";
  };

  // ---------------------------------------------------------------------------
  // JSX
  // ---------------------------------------------------------------------------

  return (
    <section className="w-full max-w-3xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Drag-and-drop zone */}
        <div
          role="button"
          tabIndex={0}
          aria-label="Upload product image"
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          className={`relative flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-8 cursor-pointer transition-colors duration-200 ${
            isDragging
              ? "border-[#10D94B] bg-[#10D94B]/5"
              : file
              ? "border-[#10D94B] bg-white"
              : "border-[#CBD5E1] bg-white hover:border-[#10D94B]"
          }`}
        >
          {preview ? (
            <div className="flex flex-col items-center gap-2">
              <img
                src={preview}
                alt="Selected product"
                className="h-32 w-32 rounded-md object-contain shadow-sm"
              />
              <span className="text-sm text-[#475569]">{file?.name}</span>
              <span className="text-xs text-[#10D94B] font-medium">
                Click or drag to replace
              </span>
            </div>
          ) : (
            <>
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#F1F5F9]">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-7 w-7 text-[#10D94B]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                  />
                </svg>
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-[#1A1C24]">
                  Drop your product image here
                </p>
                <p className="mt-1 text-xs text-[#475569]">
                  or click to browse — JPG, PNG, WEBP accepted
                </p>
              </div>
            </>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={onFileInputChange}
          />
        </div>

        {/* Email input */}
        <div>
          <label
            htmlFor="scan-email"
            className="mb-1.5 block text-sm font-medium text-[#1A1C24]"
          >
            Your email address
          </label>
          <input
            id="scan-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-md border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm text-[#1A1C24] placeholder-[#94A3B8] outline-none transition-shadow focus:border-[#10D94B] focus:ring-2 focus:ring-[#10D94B]/30"
          />
          <p className="mt-1 text-xs text-[#475569]">
            We send results and your scan report here. No spam.
          </p>
        </div>

        {/* Error state */}
        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Submit button */}
        <button
          type="submit"
          disabled={isLoading || !file || !email.trim()}
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#10D94B] px-6 py-3 text-sm font-bold text-[#1A1C24] shadow-sm transition-all duration-200 hover:scale-[1.02] hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <svg
                className="h-4 w-4 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v8H4z"
                />
              </svg>
              Scanning global marketplaces...{" "}
              {countdown > 0 ? `${countdown}s remaining` : "almost done"}
            </>
          ) : (
            <>
              Scan Now
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z"
                />
              </svg>
            </>
          )}
        </button>
      </form>

      {/* Results */}
      {response && (
        <div className="mt-10 space-y-6">
          {/* Summary stat cards */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-[#E2E8F0] bg-white p-5 text-center shadow-sm">
              <p className="text-4xl font-extrabold text-[#1A1C24]">
                {response.total_matches_found}
              </p>
              <p className="mt-1 text-sm text-[#475569]">Total matches found</p>
            </div>
            <div className="rounded-lg border border-[#E2E8F0] bg-white p-5 text-center shadow-sm">
              <p className="text-4xl font-extrabold text-red-500">
                {response.high_confidence_matches}
              </p>
              <p className="mt-1 text-sm text-[#475569]">
                High-confidence matches
              </p>
            </div>
          </div>

          {/* Result cards grid */}
          {response.results.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {response.results.map((result, idx) => (
                <div
                  key={idx}
                  className="overflow-hidden rounded-lg border border-[#E2E8F0] bg-white shadow-sm"
                >
                  {/* Thumbnail */}
                  <div className="relative h-36 w-full overflow-hidden bg-[#F1F5F9]">
                    {renderThumbnail(result)}
                    {/* Blur overlay for extra obfuscation */}
                    <div className="absolute inset-0 flex items-center justify-center backdrop-blur-[2px]">
                      <span className="rounded bg-black/40 px-2 py-0.5 text-xs font-semibold text-white">
                        Sign in to reveal
                      </span>
                    </div>
                  </div>

                  <div className="p-4 space-y-2">
                    {/* Platform badge */}
                    <div className="flex items-center justify-between">
                      <span className="inline-block rounded-full bg-[#F1F5F9] px-2.5 py-0.5 text-xs font-semibold text-[#475569]">
                        {result.platform}
                      </span>
                      <span
                        className={`text-sm font-bold ${similarityColor(
                          result.similarity_score
                        )}`}
                      >
                        {similarityPercent(result.similarity_score)} match
                      </span>
                    </div>

                    {/* Domain hint */}
                    <p className="truncate font-mono text-xs text-[#475569]">
                      {result.domain_hint}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-[#E2E8F0] bg-white px-6 py-8 text-center text-sm text-[#475569]">
              No high-similarity matches were found for this image. Your
              product appears to be safe — for now.
            </div>
          )}

          {/* CTA banner */}
          <div className="rounded-lg border border-[#10D94B] bg-[#10D94B]/5 p-6 text-center">
            <p className="text-base font-semibold text-[#1A1C24]">
              {response.cta_message}
            </p>
            <p className="mt-1 text-sm text-[#475569]">
              Get full listing URLs, seller details, and one-click takedown tools.
            </p>
            <a
              href="/auth/login"
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-[#1A1C24] px-6 py-2.5 text-sm font-bold text-white transition-all duration-200 hover:scale-105 hover:shadow-md"
            >
              Unlock Full Results &amp; Remove These Listings
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </a>
          </div>
        </div>
      )}
    </section>
  );
}
