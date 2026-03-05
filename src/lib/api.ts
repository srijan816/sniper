import { createBrowserSupabaseClient } from "./supabase/client";
import type {
  Asset,
  AuditLog,
  AuthorizedSeller,
  Client,
  ClientAnalytics,
  NotificationSettings,
  Takedown,
  Threat,
} from "./contracts";

export type {
  Asset,
  AuditLog,
  AuthorizedSeller,
  Client,
  ClientAnalytics,
  NotificationSettings,
  Takedown,
  Threat,
  ThreatStatus,
} from "./contracts";

const rawBackendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const normalizedBackendUrl = rawBackendUrl.replace(/\/$/, "");
const API_BASE = normalizedBackendUrl.endsWith("/api") ? normalizedBackendUrl : `${normalizedBackendUrl}/api`;

function apiUrl(path: string) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

async function authenticatedFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const supabase = createBrowserSupabaseClient();
  const headers = new Headers(options.headers || {});

  if (supabase) {
    const { data } = await supabase.auth.getSession();
    if (data?.session?.access_token) {
      headers.set("Authorization", `Bearer ${data.session.access_token}`);
    }
  }

  return fetch(apiUrl(path), { ...options, headers });
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function normalizeThreatStatus(status: string): string {
  if (status === "TAKEDOWN_SUBMITTED") return "SUBMITTED";
  if (status === "TAKEDOWN_CONFIRMED") return "REMOVED";
  return status;
}

export async function listThreats() {
  const response = await authenticatedFetch("/threats", { cache: "no-store" });
  return parseJson<Threat[]>(response);
}

export async function approveThreat(threatId: string) {
  const response = await authenticatedFetch(`/threats/${threatId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return parseJson<Threat>(response);
}

export async function whitelistThreat(threatId: string) {
  const response = await authenticatedFetch(`/threats/${threatId}/whitelist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return parseJson<Threat>(response);
}

export async function listThreatAuditLogs(threatId: string) {
  const response = await authenticatedFetch(`/threats/${threatId}/audit-trail`, { cache: "no-store" });
  return parseJson<AuditLog[]>(response);
}

export async function listAuditLogs(limit = 200) {
  const response = await authenticatedFetch(`/threats/audit-logs?limit=${limit}`, { cache: "no-store" });
  return parseJson<AuditLog[]>(response);
}

export async function listAssets() {
  const response = await authenticatedFetch("/assets", { cache: "no-store" });
  return parseJson<Asset[]>(response);
}

export async function uploadAsset(file: File, assetType: "IMAGE" | "VIDEO") {
  const formData = new FormData();
  formData.append("asset_type", assetType);
  formData.append("file", file);

  const response = await authenticatedFetch("/assets/upload", {
    method: "POST",
    body: formData,
  });
  return parseJson<Asset>(response);
}

export async function listTakedowns() {
  const response = await authenticatedFetch("/takedown", { cache: "no-store" });
  return parseJson<Takedown[]>(response);
}

export async function listClients() {
  const response = await authenticatedFetch("/clients", { cache: "no-store" });
  return parseJson<Client[]>(response);
}

export async function updateClient(clientId: string, patch: Record<string, unknown>) {
  const response = await authenticatedFetch(`/clients/${clientId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  return parseJson<Client>(response);
}

export async function createCheckoutSession(plan: string, successUrl: string, cancelUrl: string): Promise<string> {
  const response = await authenticatedFetch("/checkout/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan, success_url: successUrl, cancel_url: cancelUrl }),
  });
  const data = await parseJson<{ url: string }>(response);
  return data.url;
}

export async function getAdminMetrics() {
  const response = await authenticatedFetch("/admin/metrics", { cache: "no-store" });
  return parseJson<{
    total_mrr: number;
    active_clients: number;
    total_threats_discovered: number;
    total_threats_removed: number;
    threats_pending: number;
    dlq_count: number;
  }>(response);
}

export async function getAdminDlq() {
  const response = await authenticatedFetch("/admin/dlq", { cache: "no-store" });
  return parseJson<Array<{
    id: string;
    takedown_id?: string;
    error_reason: string;
    failed_at: string;
  }>>(response);
}

export async function retryDlqEntry(dlqId: string) {
  const response = await authenticatedFetch(`/admin/dlq/${dlqId}/retry`, { method: "POST" });
  return parseJson<{ status: string }>(response);
}

export async function dismissDlqEntry(dlqId: string) {
  const response = await authenticatedFetch(`/admin/dlq/${dlqId}/dismiss`, { method: "POST" });
  return parseJson<{ status: string }>(response);
}

export async function getClientAnalytics() {
  const response = await authenticatedFetch("/clients/me/analytics", { cache: "no-store" });
  return parseJson<ClientAnalytics>(response);
}

export async function listAuthorizedSellers(clientId: string) {
  const response = await authenticatedFetch(`/clients/${clientId}/authorized-sellers`, { cache: "no-store" });
  return parseJson<AuthorizedSeller[]>(response);
}

export async function addAuthorizedSeller(
  clientId: string,
  payload: { domain: string; seller_name?: string; platform?: string; relationship?: string }
) {
  const response = await authenticatedFetch(`/clients/${clientId}/authorized-sellers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<AuthorizedSeller>(response);
}

export async function removeAuthorizedSeller(clientId: string, sellerId: string) {
  const response = await authenticatedFetch(`/clients/${clientId}/authorized-sellers/${sellerId}`, {
    method: "DELETE",
  });
  return parseJson<{ status: string }>(response);
}

export async function getNotificationSettings(clientId: string) {
  const response = await authenticatedFetch(`/clients/${clientId}/notifications`, { cache: "no-store" });
  return parseJson<NotificationSettings>(response);
}

export async function updateNotificationSettings(
  clientId: string,
  payload: { slack_webhook_url?: string | null; webhook_url?: string | null; notification_prefs?: Record<string, unknown> }
) {
  const response = await authenticatedFetch(`/clients/${clientId}/notifications`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<NotificationSettings>(response);
}

export async function testNotification(clientId: string, channel: "email" | "slack" | "webhook") {
  const response = await authenticatedFetch(`/clients/${clientId}/notifications/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel }),
  });
  return parseJson<{ status: string; message: string }>(response);
}

export async function freeScan(formData: FormData) {
  const rawBackendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  const base = rawBackendUrl.replace(/\/$/, "");
  const response = await fetch(`${base}/api/scan/free`, { method: "POST", body: formData });
  return parseJson<{
    total_matches_found: number;
    high_confidence_matches: number;
    results: Array<{ platform: string; country: string; similarity_score: number; thumbnail_url: string | null; domain_hint: string }>;
    email_captured: boolean;
    cta_message: string;
  }>(response);
}
