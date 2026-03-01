export type ThreatStatus =
  | "DISCOVERED"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "WHITELISTED"
  | "REJECTED"
  | "TAKEDOWN_SUBMITTED"
  | "TAKEDOWN_CONFIRMED"
  | "REMOVED";

export type Threat = {
  id: string;
  asset_id: string;
  client_id: string;
  infringing_url: string;
  infringing_image_url?: string | null;
  host_domain: string;
  similarity_score: number;
  status: ThreatStatus;
  discovered_at: string;
  ai_explanation?: string | null;
  resolved_at?: string | null;
};

export type Asset = {
  id: string;
  client_id: string;
  asset_type: "IMAGE" | "VIDEO";
  original_filename: string;
  storage_url: string;
  thumbnail_url?: string | null;
  status: string;
  created_at: string;
};

export type Takedown = {
  id: string;
  threat_id: string;
  platform: string;
  case_number?: string | null;
  status: "PENDING" | "SUBMITTED" | "CONFIRMED" | "FAILED";
  retry_count: number;
  submitted_at?: string | null;
  completed_at?: string | null;
  created_at: string;
};

export type Client = {
  id: string;
  company_name: string;
  subscription_tier: "FREE" | "STARTER" | "GROWTH" | "AGENCY";
  monthly_threat_limit: number;
  current_month_count: number;
};

export type AuditLog = {
  id: string;
  threat_id: string;
  old_status?: string | null;
  new_status: string;
  changed_by: string;
  changed_at: string;
};

import { createBrowserSupabaseClient } from "./supabase/client";

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
  // Path param is ignored by backend; client_id comes from JWT via Depends()
  const response = await authenticatedFetch("/clients/me/analytics", { cache: "no-store" });
  return parseJson<{
    threats_found_this_month: number;
    threats_removed_this_month: number;
    estimated_revenue_protected: number;
    average_order_value: number;
  }>(response);
}
