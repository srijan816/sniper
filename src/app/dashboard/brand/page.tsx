"use client";

import { useEffect, useRef, useState } from "react";
import { listClients, updateClient, getNotificationSettings, updateNotificationSettings, testNotification } from "@/lib/api";

type ClientData = {
  id: string;
  company_name: string;
  legal_contact_name: string;
  legal_contact_email: string;
  contact_address: string;
  contact_phone: string;
};

type Tab = "profile" | "notifications";

export default function BrandProfilePage() {
  const [tab, setTab] = useState<Tab>("profile");
  const [client, setClient] = useState<ClientData | null>(null);
  const [form, setForm] = useState({ company_name: "", legal_contact_name: "", legal_contact_email: "", contact_address: "", contact_phone: "" });
  const [notifForm, setNotifForm] = useState({ slack_webhook_url: "", webhook_url: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listClients()
      .then(async (clients) => {
        const c = clients[0];
        if (!c) return;
        const raw = c as Record<string, unknown>;
        const data: ClientData = {
          id: c.id,
          company_name: c.company_name,
          legal_contact_name: raw.legal_contact_name as string ?? "",
          legal_contact_email: raw.legal_contact_email as string ?? "",
          contact_address: raw.contact_address as string ?? "",
          contact_phone: raw.contact_phone as string ?? "",
        };
        setClient(data);
        setForm({
          company_name: data.company_name,
          legal_contact_name: data.legal_contact_name,
          legal_contact_email: data.legal_contact_email,
          contact_address: data.contact_address,
          contact_phone: data.contact_phone,
        });
        try {
          const ns = await getNotificationSettings(c.id);
          setNotifForm({
            slack_webhook_url: ns.slack_webhook_url || "",
            webhook_url: ns.webhook_url || "",
          });
        } catch {
          // notification settings are optional
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

  async function handleSaveNotifications() {
    if (!client) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await updateNotificationSettings(client.id, {
        slack_webhook_url: notifForm.slack_webhook_url || null,
        webhook_url: notifForm.webhook_url || null,
      });
      setSuccess("Notification settings saved.");
    } catch {
      setError("Failed to save notification settings");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(channel: "email" | "slack" | "webhook") {
    if (!client) return;
    setTesting(channel);
    setError(null);
    setSuccess(null);
    try {
      const res = await testNotification(client.id, channel);
      setSuccess(res.message || "Test sent.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Test failed");
    } finally {
      setTesting(null);
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
        <p className="text-app-base text-muted-foreground">Configure legal contacts, LOA metadata, and notification settings.</p>
      </header>

      {error ? <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p> : null}
      {success ? <p className="rounded-md border border-green-300 bg-green-50 p-3 text-app-sm text-green-700">{success}</p> : null}

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(["profile", "notifications"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => { setTab(t); setError(null); setSuccess(null); }}
            className={`px-4 py-2 text-app-sm font-medium capitalize border-b-2 -mb-px transition-colors ${
              tab === t
                ? "border-sniper-green text-sniper-green"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-app-sm text-muted-foreground">Loading…</p>
      ) : tab === "profile" ? (
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
          <label className="block space-y-1">
            <span className="text-app-sm font-medium">Phone Number</span>
            <span className="text-app-xs text-muted-foreground ml-1">(required for DMCA notices — 17 U.S.C. § 512(c)(3))</span>
            <input
              type="tel"
              value={form.contact_phone}
              onChange={(e) => setForm((f) => ({ ...f, contact_phone: e.target.value }))}
              placeholder="+1 (555) 000-0000"
              className="h-9 w-full rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-app-sm font-medium">Business Address</span>
            <span className="text-app-xs text-muted-foreground ml-1">(required for DMCA notices — 17 U.S.C. § 512(c)(3))</span>
            <textarea
              rows={2}
              value={form.contact_address}
              onChange={(e) => setForm((f) => ({ ...f, contact_address: e.target.value }))}
              placeholder="123 Main St, Suite 100, New York, NY 10001"
              className="w-full rounded-md border bg-white px-3 py-2 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
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
      ) : (
        <section className="rounded-md border bg-card p-6 shadow-sniper-sm space-y-6">
          <div className="space-y-4">
            <p className="text-app-sm font-semibold">Slack Notifications</p>
            <label className="block space-y-1">
              <span className="text-app-xs text-muted-foreground">Slack Incoming Webhook URL</span>
              <input
                type="url"
                value={notifForm.slack_webhook_url}
                onChange={(e) => setNotifForm((f) => ({ ...f, slack_webhook_url: e.target.value }))}
                placeholder="https://hooks.slack.com/services/…"
                className="h-9 w-full rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
              />
            </label>
            <button
              type="button"
              disabled={!notifForm.slack_webhook_url || testing === "slack"}
              onClick={() => handleTest("slack")}
              className="inline-flex rounded-md border px-3 py-1.5 text-app-xs font-medium disabled:opacity-50"
            >
              {testing === "slack" ? "Sending…" : "Send Test Message"}
            </button>
          </div>

          <hr className="border-border" />

          <div className="space-y-4">
            <p className="text-app-sm font-semibold">Webhook Notifications</p>
            <label className="block space-y-1">
              <span className="text-app-xs text-muted-foreground">Webhook Endpoint URL</span>
              <input
                type="url"
                value={notifForm.webhook_url}
                onChange={(e) => setNotifForm((f) => ({ ...f, webhook_url: e.target.value }))}
                placeholder="https://your-app.com/webhooks/sniperip"
                className="h-9 w-full rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
              />
            </label>
            <p className="text-app-xs text-muted-foreground">
              Events are signed with HMAC-SHA256. Check the <code className="font-mono">X-SniperIP-Signature</code> header to verify authenticity.
            </p>
            <button
              type="button"
              disabled={!notifForm.webhook_url || testing === "webhook"}
              onClick={() => handleTest("webhook")}
              className="inline-flex rounded-md border px-3 py-1.5 text-app-xs font-medium disabled:opacity-50"
            >
              {testing === "webhook" ? "Sending…" : "Send Test Event"}
            </button>
          </div>

          <hr className="border-border" />

          <div className="flex gap-3">
            <button
              type="button"
              disabled={saving}
              onClick={handleSaveNotifications}
              className="inline-flex rounded-md bg-sniper-charcoal px-4 py-2 text-app-sm font-semibold text-white disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save Notification Settings"}
            </button>
            <button
              type="button"
              disabled={testing === "email"}
              onClick={() => handleTest("email")}
              className="inline-flex rounded-md border px-4 py-2 text-app-sm font-medium disabled:opacity-60"
            >
              {testing === "email" ? "Sending…" : "Test Email"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
