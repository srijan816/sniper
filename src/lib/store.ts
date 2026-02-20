import { create } from "zustand";

// ============================================
// Types
// ============================================
export interface Client {
    id: string;
    company_name: string;
    legal_contact_name: string;
    legal_contact_email: string;
    subscription_tier: "FREE" | "STARTER" | "GROWTH" | "AGENCY";
    monthly_threat_limit: number;
    current_month_count: number;
    loa_signed_at: string | null;
    whitelist_domains: string[];
    created_at: string;
}

export interface Threat {
    id: string;
    asset_id: string;
    client_id: string;
    infringing_url: string;
    infringing_image_url: string | null;
    host_domain: string;
    seller_name: string | null;
    listing_title: string | null;
    listing_price: number | null;
    similarity_score: number;
    status: string;
    discovered_at: string;
    resolved_at: string | null;
}

export interface Asset {
    id: string;
    client_id: string;
    asset_type: "IMAGE" | "VIDEO";
    original_filename: string;
    storage_url: string;
    thumbnail_url: string | null;
    status: string;
    created_at: string;
}

export interface AuditLog {
    id: string;
    threat_id: string;
    old_status: string | null;
    new_status: string;
    changed_by: string;
    metadata: Record<string, unknown>;
    changed_at: string;
}

export interface DLQEntry {
    id: string;
    takedown_id: string;
    error_reason: string;
    stack_trace: string | null;
    resolved: boolean;
    resolved_at: string | null;
    failed_at: string;
}

export interface AdminMetrics {
    total_mrr: number;
    active_clients: number;
    total_threats_discovered: number;
    total_threats_removed: number;
    threats_pending: number;
    dlq_count: number;
}

export interface CostMetrics {
    serpapi_credits_used: number;
    serpapi_credits_limit: number;
    hf_compute_hours: number;
    zenrows_bandwidth_mb: number;
}

export interface ClientAnalytics {
    threats_found_this_month: number;
    threats_removed_this_month: number;
    estimated_revenue_protected: number;
    average_order_value: number;
}

// ============================================
// Auth Store
// ============================================
interface AuthState {
    user: { email: string; id: string } | null;
    client: Client | null;
    isLoading: boolean;
    isAdmin: boolean;
    setUser: (user: { email: string; id: string } | null) => void;
    setClient: (client: Client | null) => void;
    setLoading: (loading: boolean) => void;
    logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    client: null,
    isLoading: true,
    isAdmin: false,
    setUser: (user) => set({ user }),
    setClient: (client) =>
        set({ client, isAdmin: false }), // Admin check would use Supabase metadata
    setLoading: (isLoading) => set({ isLoading }),
    logout: () => set({ user: null, client: null, isAdmin: false }),
}));

// ============================================
// Threat Store
// ============================================
interface ThreatState {
    threats: Threat[];
    selectedThreat: Threat | null;
    filter: string;
    isLoading: boolean;
    setThreats: (threats: Threat[]) => void;
    addThreat: (threat: Threat) => void;
    updateThreat: (id: string, updates: Partial<Threat>) => void;
    selectThreat: (threat: Threat | null) => void;
    setFilter: (filter: string) => void;
    setLoading: (loading: boolean) => void;
}

export const useThreatStore = create<ThreatState>((set) => ({
    threats: [],
    selectedThreat: null,
    filter: "ALL",
    isLoading: false,
    setThreats: (threats) => set({ threats }),
    addThreat: (threat) =>
        set((state) => ({ threats: [threat, ...state.threats] })),
    updateThreat: (id, updates) =>
        set((state) => ({
            threats: state.threats.map((t) =>
                t.id === id ? { ...t, ...updates } : t
            ),
        })),
    selectThreat: (selectedThreat) => set({ selectedThreat }),
    setFilter: (filter) => set({ filter }),
    setLoading: (isLoading) => set({ isLoading }),
}));

// ============================================
// Onboarding Store
// ============================================
interface OnboardingState {
    step: number;
    totalSteps: number;
    companyName: string;
    legalEmail: string;
    loaSigned: boolean;
    billingComplete: boolean;
    assetUploaded: boolean;
    setStep: (step: number) => void;
    nextStep: () => void;
    prevStep: () => void;
    setCompanyName: (name: string) => void;
    setLegalEmail: (email: string) => void;
    setLoaSigned: (signed: boolean) => void;
    setBillingComplete: (complete: boolean) => void;
    setAssetUploaded: (uploaded: boolean) => void;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
    step: 1,
    totalSteps: 4,
    companyName: "",
    legalEmail: "",
    loaSigned: false,
    billingComplete: false,
    assetUploaded: false,
    setStep: (step) => set({ step }),
    nextStep: () => set((state) => ({ step: Math.min(state.step + 1, state.totalSteps) })),
    prevStep: () => set((state) => ({ step: Math.max(state.step - 1, 1) })),
    setCompanyName: (companyName) => set({ companyName }),
    setLegalEmail: (legalEmail) => set({ legalEmail }),
    setLoaSigned: (loaSigned) => set({ loaSigned }),
    setBillingComplete: (billingComplete) => set({ billingComplete }),
    setAssetUploaded: (assetUploaded) => set({ assetUploaded }),
}));
