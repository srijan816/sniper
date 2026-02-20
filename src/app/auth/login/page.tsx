"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, Mail } from "lucide-react";
import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setSent(true);
    }, 1100);
  };

  return (
    <div className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto w-full max-w-[440px] rounded-md border bg-white p-8 shadow-sniper-lg">
        <Link href="/" className="mb-6 inline-flex items-center gap-2 text-app-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Back to home
        </Link>

        <Image src="/logo-dark.png" alt="SniperIP" width={200} height={200} className="h-12 w-auto" />

        <h1 className="mt-4 font-heading text-app-2xl font-bold">Welcome back</h1>
        <p className="mt-1 text-app-base text-muted-foreground">Sign in with a magic link. No password required.</p>

        {!sent ? (
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block space-y-1">
              <span className="text-app-sm font-medium text-foreground">Email address</span>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@company.com"
                  className="h-10 w-full rounded-md border bg-white pl-9 pr-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
                />
              </div>
            </label>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-10 w-full items-center justify-center rounded-md bg-sniper-charcoal text-app-sm font-semibold text-white disabled:opacity-60"
            >
              {loading ? "Sending..." : "Send Magic Link"}
            </button>
          </form>
        ) : (
          <div className="mt-6 space-y-2 rounded-md border border-sniper-green bg-sniper-green-muted p-4">
            <p className="text-app-sm font-semibold text-sniper-charcoal">Magic link sent</p>
            <p className="text-app-sm text-muted-foreground">
              We sent a sign-in link to <span className="font-medium text-foreground">{email}</span>.
            </p>
            <Link href="/dashboard" className="inline-flex text-app-sm font-medium text-[#0A7C2E] underline">
              Continue to demo dashboard
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
