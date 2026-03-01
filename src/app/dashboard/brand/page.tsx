"use client";

import { useEffect, useRef, useState } from "react";
import { listClients, updateClient } from "@/lib/api";

type ClientData = {
  id: string;
  company_name: string;
  legal_contact_name: string;
  legal_contact_email: string;
};

export default function BrandProfilePage() {
  const [client, setClient] = useState<ClientData | null>(null);
  const [form, setForm] = useState({ company_name: "", legal_contact_name: "", legal_contact_email: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listClients()
      .then((clients) => {
        const c = clients[0];
        if (c) {
          const data: ClientData = {
            id: c.id,
            company_name: c.company_name,
            legal_contact_name: (c as Record<string, unknown>).legal_contact_name as string ?? "",
            legal_contact_email: (c as Record<string, unknown>).legal_contact_email as string ?? "",
          };
          setClient(data);
          setForm({
            company_name: data.company_name,
            legal_contact_name: data.legal_contact_name,
            legal_contact_email: data.legal_contact_email,
          });
        }
      })
      .catch(() => setError("Failed to load brand profile"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    if (!client) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await updateClient(client.id, form);
      setSuccess("Brand profile saved.");
    } catch {
      setError("Failed to save brand profile");
    } finally {
      setSaving(false);
    }
  }

  async function handleLoaUpload(file: File) {
    if (!client) return;
    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const { createBrowserSupabaseClient } = await import("@/lib/supabase/client");
      const supabase = createBrowserSupabaseClient();
      const { data: sessionData } = await supabase!.auth.getSession();
      const token = sessionData?.session?.access_token;

      const rawBackendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const base = rawBackendUrl.replace(/\/$/, "");
      const url = `${base}/api/clients/${client.id}/loa-upload`;

      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(url, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      setSuccess("LOA uploaded successfully.");
    } catch {
      setError("Failed to upload LOA");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Brand Profile</h1>
        <p className="text-app-base text-muted-foreground">Configure legal contacts, LOA metadata, and brand identity settings.</p>
      </header>

      {error ? <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p> : null}
      {success ? <p className="rounded-md border border-green-300 bg-green-50 p-3 text-app-sm text-green-700">{success}</p> : null}

      {loading ? (
        <p className="text-app-sm text-muted-foreground">Loading…</p>
      ) : (
        <section className="rounded-md border bg-card p-6 shadow-sniper-sm space-y-4">
          <label className="block space-y-1">
            <span className="text-app-sm font-medium">Company Name</span>
            <input
              value={form.company_name}
              onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
              className="h-9 w-full rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-app-sm font-medium">Legal Contact Name</span>
            <input
              value={form.legal_contact_name}
              onChange={(e) => setForm((f) => ({ ...f, legal_contact_name: e.target.value }))}
              className="h-9 w-full rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-app-sm font-medium">Legal Contact Email</span>
            <input
              type="email"
              value={form.legal_contact_email}
              onChange={(e) => setForm((f) => ({ ...f, legal_contact_email: e.target.value }))}
              className="h-9 w-full rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
            />
          </label>

          <div className="flex gap-3">
            <button
              type="button"
              disabled={saving}
              onClick={handleSave}
              className="inline-flex rounded-md bg-sniper-charcoal px-4 py-2 text-app-sm font-semibold text-white disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>

          <hr className="border-border" />

          <div className="space-y-2">
            <p className="text-app-sm font-medium">Letter of Authorization (LOA)</p>
            <p className="text-app-xs text-muted-foreground">Upload a signed PDF authorizing SniperIP to enforce DMCA notices on your behalf.</p>
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleLoaUpload(file);
              }}
            />
            <button
              type="button"
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
              className="inline-flex rounded-md border px-4 py-2 text-app-sm font-medium disabled:opacity-60"
            >
              {uploading ? "Uploading…" : "Upload LOA PDF"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
