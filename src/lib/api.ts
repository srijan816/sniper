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

const rawBackendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const normalizedBackendUrl = rawBackendUrl.replace(/\/$/, "");
const API_BASE = normalizedBackendUrl.endsWith("/api") ? normalizedBackendUrl : `${normalizedBackendUrl}/api`;

function apiUrl(path: string) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
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
  const response = await fetch(apiUrl("/threats"), { cache: "no-store" });
  return parseJson<Threat[]>(response);
}

export async function approveThreat(threatId: string) {
  const response = await fetch(apiUrl(`/threats/${threatId}/approve`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return parseJson<Threat>(response);
}

export async function whitelistThreat(threatId: string) {
  const response = await fetch(apiUrl(`/threats/${threatId}/whitelist`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return parseJson<Threat>(response);
}

export async function listThreatAuditLogs(threatId: string) {
  const response = await fetch(apiUrl(`/threats/${threatId}/audit-trail`), { cache: "no-store" });
  return parseJson<AuditLog[]>(response);
}

export async function listAuditLogs(limit = 200) {
  const response = await fetch(apiUrl(`/threats/audit-logs?limit=${limit}`), { cache: "no-store" });
  return parseJson<AuditLog[]>(response);
}

export async function listAssets() {
  const response = await fetch(apiUrl("/assets"), { cache: "no-store" });
  return parseJson<Asset[]>(response);
}

export async function uploadAsset(file: File, assetType: "IMAGE" | "VIDEO", clientId = "self-serve-client") {
  const formData = new FormData();
  formData.append("client_id", clientId);
  formData.append("asset_type", assetType);
  formData.append("file", file);

  const response = await fetch(apiUrl("/assets/upload"), {
    method: "POST",
    body: formData,
  });
  return parseJson<Asset>(response);
}

export async function listTakedowns() {
  const response = await fetch(apiUrl("/takedown"), { cache: "no-store" });
  return parseJson<Takedown[]>(response);
}

export async function listClients() {
  const response = await fetch(apiUrl("/clients"), { cache: "no-store" });
  return parseJson<Client[]>(response);
}
