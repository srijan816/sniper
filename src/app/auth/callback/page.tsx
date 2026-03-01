"use client";

import type { EmailOtpType } from "@supabase/supabase-js";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createBrowserSupabaseClient } from "@/lib/supabase/client";

function normalizeNext(value: string | null): string {
  if (!value) return "/dashboard";
  return value.startsWith("/") ? value : "/dashboard";
}

function loginErrorPath() {
  return "/auth/login?error=auth_callback_failed";
}

export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    async function finishAuth() {
      const supabase = createBrowserSupabaseClient();
      if (!supabase) {
        router.replace(loginErrorPath());
        return;
      }

      const query = new URLSearchParams(window.location.search);
      const next = normalizeNext(query.get("next"));
      const code = query.get("code");
      const tokenHash = query.get("token_hash");
      const type = query.get("type") as EmailOtpType | null;

      try {
        if (code) {
          const { error } = await supabase.auth.exchangeCodeForSession(code);
          if (!error && !cancelled) {
            router.replace(next);
            return;
          }
        }

        if (tokenHash && type) {
          const { error } = await supabase.auth.verifyOtp({
            type,
            token_hash: tokenHash,
          });
          if (!error && !cancelled) {
            router.replace(next);
            return;
          }
        }

        const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
        const accessToken = hash.get("access_token");
        const refreshToken = hash.get("refresh_token");
        if (accessToken && refreshToken) {
          const { error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
          if (!error && !cancelled) {
            router.replace(next);
            return;
          }
        }

        const { data } = await supabase.auth.getSession();
        if (data.session && !cancelled) {
          router.replace(next);
          return;
        }
      } catch {
        // Fall through to login error path.
      }

      if (!cancelled) {
        router.replace(loginErrorPath());
      }
    }

    void finishAuth();
    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <div className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto w-full max-w-[520px] rounded-md border bg-white p-8 shadow-sniper-lg">
        <h1 className="font-heading text-app-xl font-semibold text-foreground">Completing sign-in</h1>
        <p className="mt-2 text-app-sm text-muted-foreground">
          We are finalizing your authentication. You will be redirected automatically.
        </p>
      </div>
    </div>
  );
}
