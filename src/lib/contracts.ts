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
  seller_name?: string | null;
  listing_title?: string | null;
  listing_price?: number | null;
  similarity_score: number;
  estimated_stock?: number | null;
  financial_impact?: number | null;
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
  legal_contact_name?: string;
  legal_contact_email?: string;
  subscription_tier: "FREE" | "STARTER" | "GROWTH" | "AGENCY";
  monthly_threat_limit: number;
  current_month_count: number;
  loa_signed_at?: string | null;
  whitelist_domains?: string[];
  automation_rules?: Record<string, unknown>;
  created_at?: string;
  contact_address?: string;
  contact_phone?: string;
};

export type AuditLog = {
  id: string;
  threat_id: string;
  old_status?: string | null;
  new_status: string;
  changed_by: string;
  metadata?: Record<string, unknown>;
  changed_at: string;
};

export type ClientAnalytics = {
  threats_found_this_month: number;
  threats_removed_this_month: number;
  estimated_revenue_protected: number;
  average_order_value: number;
  threats_discovered_total: number;
  takedowns_completed_total: number;
  takedowns_completed_this_month: number;
  average_time_to_takedown_hours: number | null;
  bad_actors_identified: number;
  platforms_breakdown: Record<string, number>;
  monthly_trend: Array<{ month: string; threats: number; takedowns: number }>;
};

export type AuthorizedSeller = {
  id: string;
  client_id: string;
  domain: string;
  seller_name?: string | null;
  platform?: string | null;
  platform_seller_id?: string | null;
  relationship: string;
  added_by: string;
  created_at: string;
};

export type NotificationSettings = {
  slack_webhook_url: string | null;
  webhook_url: string | null;
  webhook_secret: string | null;
  notification_prefs: Record<string, unknown>;
};
