"use client";

import { useEffect, useState } from "react";
import { listClients, updateClient } from "@/lib/api";

export default function WhitelistPage() {
  const [domains, setDomains] = useState<string[]>([]);
  const [clientId, setClientId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listClients()
      .then((clients) => {
        const client = clients[0];
        if (client) {
          setClientId(client.id);
          // whitelist_domains is not in Client type yet — cast to any to access it
          const raw = (client as Record<string, unknown>).whitelist_domains;
          setDomains(Array.isArray(raw) ? (raw as string[]) : []);
        }
      })
      .catch(() => setError("Failed to load whitelist"))
      .finally(() => setLoading(false));
  }, []);

  async function save(updated: string[]) {
    if (!clientId) return;
    setSaving(true);
    setError(null);
    try {
      await updateClient(clientId, { whitelist_domains: updated });
      setDomains(updated);
    } catch {
      setError("Failed to save whitelist");
    } finally {
      setSaving(false);
    }
  }

  function addDomain() {
    const trimmed = input.trim().toLowerCase().replace(/^https?:\/\//, "");
    if (!trimmed || domains.includes(trimmed)) {
      setInput("");
      return;
    }
    save([...domains, trimmed]);
    setInput("");
  }

  function removeDomain(domain: string) {
    save(domains.filter((d) => d !== domain));
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-app-2xl font-bold">Whitelist</h1>
        <p className="text-app-base text-muted-foreground">Protect authorized distributors from accidental enforcement.</p>
      </header>

      {error ? <p className="rounded-md border border-red-300 bg-red-50 p-3 text-app-sm text-red-700">{error}</p> : null}

      <section className="rounded-md border bg-card p-6 shadow-sniper-sm space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addDomain()}
            placeholder="authorized-retailer.com"
            className="h-9 flex-1 rounded-md border bg-white px-3 text-app-sm outline-none focus:border-sniper-green focus:ring-2 focus:ring-sniper-green/30"
          />
          <button
            type="button"
            disabled={saving || !input.trim()}
            onClick={addDomain}
            className="inline-flex rounded-md bg-sniper-charcoal px-4 py-2 text-app-sm font-semibold text-white disabled:opacity-60"
          >
            {saving ? "Saving…" : "Add"}
          </button>
        </div>

        {loading ? (
          <p className="text-app-sm text-muted-foreground">Loading…</p>
        ) : domains.length === 0 ? (
          <p className="text-app-sm text-muted-foreground">No whitelisted domains yet.</p>
        ) : (
          <ul className="space-y-2">
            {domains.map((domain) => (
              <li key={domain} className="flex items-center justify-between rounded-sm border bg-white px-3 py-2">
                <span className="font-mono text-app-sm">{domain}</span>
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => removeDomain(domain)}
                  className="text-app-xs text-red-500 hover:underline disabled:opacity-50"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
