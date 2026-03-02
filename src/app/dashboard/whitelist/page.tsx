"use client";

import { useEffect, useState } from "react";
import { listClients, listAuthorizedSellers, addAuthorizedSeller, removeAuthorizedSeller } from "@/lib/api";
import type { AuthorizedSeller } from "@/lib/api";

const RELATIONSHIPS = ["authorized_distributor", "official_retailer", "licensee", "own_property"] as const;

export default function WhitelistPage() {
  const [sellers, setSellers] = useState<AuthorizedSeller[]>([]);
  const [clientId, setClientId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    domain: "",
    seller_name: "",
    platform: "",
    relationship: "authorized_distributor" as string,
  });

  useEffect(() => {
    listClients()
      .then(async (clients) => {
        const client = clients[0];
        if (!client) return;
        setClientId(client.id);
        const data = await listAuthorizedSellers(client.id);
        setSellers(data);
      })
      .catch(() => setError("Failed to load whitelist"))
      .finally(() => setLoading(false));
  }, []);

  async function handleAdd() {
    if (!clientId || !form.domain.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const domain = form.domain.trim().toLowerCase().replace(/^https?:\/\//, "");
      const seller = await addAuthorizedSeller(clientId, {
        domain,
        seller_name: form.seller_name.trim() || undefined,
        platform: form.platform.trim() || undefined,
        relationship: form.relationship,
      });
      setSellers((prev) => [...prev, seller]);
      setForm({ domain: "", seller_name: "", platform: "", relationship: "authorized_distributor" });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to add seller");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove(sellerId: string) {
    if (!clientId) return;
    setSaving(true);
    setError(null);
    try {
      await removeAuthorizedSeller(clientId, sellerId);
      setSellers((prev) => prev.filter((s) => s.id !== sellerId));
    } catch {
      setError("Failed to remove seller");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Authorized Sellers</h1>
        <p className="text-app-base text-muted-foreground">
          Protect authorized distributors and retailers from accidental enforcement.
        </p>
      </header>

      {error ? (
        <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p>
      ) : null}

      <section className="rounded-md border bg-card p-6 shadow-sniper-sm space-y-4">
        <p className="text-app-sm font-semibold">Add Authorized Seller</p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <input
            type="text"
            value={form.domain}
            onChange={(e) => setForm((f) => ({ ...f, domain: e.target.value }))}
            placeholder="authorized-retailer.com *"
            className="h-9 rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
          />
          <input
            type="text"
            value={form.seller_name}
            onChange={(e) => setForm((f) => ({ ...f, seller_name: e.target.value }))}
            placeholder="Seller name (optional)"
            className="h-9 rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
          />
          <input
            type="text"
            value={form.platform}
            onChange={(e) => setForm((f) => ({ ...f, platform: e.target.value }))}
            placeholder="Platform (e.g. Shopify, Amazon)"
            className="h-9 rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
          />
          <select
            value={form.relationship}
            onChange={(e) => setForm((f) => ({ ...f, relationship: e.target.value }))}
            className="h-9 rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
          >
            {RELATIONSHIPS.map((r) => (
              <option key={r} value={r}>
                {r.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          disabled={saving || !form.domain.trim()}
          onClick={handleAdd}
          className="inline-flex rounded-md bg-sniper-charcoal px-4 py-2 text-app-sm font-semibold text-white disabled:opacity-60"
        >
          {saving ? "Saving…" : "Add Seller"}
        </button>
      </section>

      <section className="rounded-md border bg-card shadow-sniper-sm overflow-hidden">
        {loading ? (
          <p className="p-6 text-app-sm text-muted-foreground">Loading…</p>
        ) : sellers.length === 0 ? (
          <p className="p-6 text-app-sm text-muted-foreground">No authorized sellers yet.</p>
        ) : (
          <table className="w-full text-app-sm">
            <thead className="border-b bg-muted/30">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Domain</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Seller</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Platform</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Relationship</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {sellers.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-3 font-mono">{s.domain}</td>
                  <td className="px-4 py-3 text-muted-foreground">{s.seller_name || "—"}</td>
                  <td className="px-4 py-3 text-muted-foreground">{s.platform || "—"}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-sm bg-muted px-2 py-0.5 text-app-xs capitalize">
                      {s.relationship.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      disabled={saving}
                      onClick={() => handleRemove(s.id)}
                      className="text-app-xs text-red-500 hover:underline disabled:opacity-50"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
