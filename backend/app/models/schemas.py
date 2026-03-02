"""Pydantic models for SniperIP API"""
from pydantic import BaseModel, Field, AnyHttpUrl, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================
# ENUMS
# ============================================
class SubscriptionTier(str, Enum):
    FREE = "FREE"
    STARTER = "STARTER"
    GROWTH = "GROWTH"
    AGENCY = "AGENCY"


class AssetType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class ThreatStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    WHITELISTED = "WHITELISTED"
    REJECTED = "REJECTED"
    TAKEDOWN_SUBMITTED = "TAKEDOWN_SUBMITTED"
    TAKEDOWN_CONFIRMED = "TAKEDOWN_CONFIRMED"
    REMOVED = "REMOVED"


class ActorType(str, Enum):
    SYSTEM = "SYSTEM"
    CLIENT_USER = "CLIENT_USER"
    ADMIN = "ADMIN"


class TakedownStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


# ============================================
# CLIENT SCHEMAS
# ============================================
class ClientBase(BaseModel):
    company_name: str
    legal_contact_name: str
    legal_contact_email: str


class ClientCreate(ClientBase):
    pass


class ClientResponse(ClientBase):
    id: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    monthly_threat_limit: int = 0
    current_month_count: int = 0
    loa_signed_at: Optional[datetime] = None
    whitelist_domains: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# ASSET SCHEMAS
# ============================================
class AssetCreate(BaseModel):
    asset_type: AssetType = AssetType.IMAGE
    original_filename: str
    storage_url: AnyHttpUrl
    thumbnail_url: Optional[AnyHttpUrl] = None


class AssetResponse(BaseModel):
    id: str
    client_id: str
    asset_type: AssetType
    original_filename: str
    storage_url: str
    thumbnail_url: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# THREAT SCHEMAS
# ============================================
class ThreatCreate(BaseModel):
    asset_id: str
    client_id: str
    infringing_url: AnyHttpUrl
    infringing_image_url: Optional[AnyHttpUrl] = None
    host_domain: str
    seller_name: Optional[str] = None
    listing_title: Optional[str] = None
    listing_price: Optional[float] = Field(default=None, ge=0)
    similarity_score: float = Field(ge=0.0, le=1.0)
    ai_explanation: Optional[str] = None


class ThreatResponse(BaseModel):
    id: str
    asset_id: str
    client_id: str
    infringing_url: str
    infringing_image_url: Optional[str] = None
    host_domain: str
    seller_name: Optional[str] = None
    listing_title: Optional[str] = None
    listing_price: Optional[float] = None
    similarity_score: float
    ai_explanation: Optional[str] = None
    status: ThreatStatus
    discovered_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ThreatStatusUpdate(BaseModel):
    status: ThreatStatus
    changed_by: ActorType
    metadata: Optional[dict] = None


# ============================================
# AUDIT LOG SCHEMAS
# ============================================
class AuditLogResponse(BaseModel):
    id: str
    threat_id: str
    old_status: Optional[str] = None
    new_status: str
    changed_by: str
    metadata: Optional[dict] = None
    changed_at: datetime

    class Config:
        from_attributes = True


# ============================================
# TAKEDOWN SCHEMAS
# ============================================
class TakedownCreate(BaseModel):
    threat_id: str
    platform: str


class TakedownResponse(BaseModel):
    id: str
    threat_id: str
    platform: str
    case_number: Optional[str] = None
    status: TakedownStatus
    retry_count: int
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# DLQ SCHEMAS
# ============================================
class DLQEntry(BaseModel):
    id: str
    takedown_id: str
    error_reason: str
    stack_trace: Optional[str] = None
    resolved: bool
    resolved_at: Optional[datetime] = None
    failed_at: datetime

    class Config:
        from_attributes = True


# ============================================
# ADMIN / METRICS SCHEMAS
# ============================================
class AdminMetrics(BaseModel):
    total_mrr: float
    active_clients: int
    total_threats_discovered: int
    total_threats_removed: int
    threats_pending: int
    dlq_count: int


class CostMetrics(BaseModel):
    serpapi_credits_used: int
    serpapi_credits_limit: int
    hf_compute_hours: float
    zenrows_bandwidth_mb: float


class ClientAnalytics(BaseModel):
    threats_found_this_month: int
    threats_removed_this_month: int
    estimated_revenue_protected: float
    average_order_value: float
    # Extended analytics (PID Feature 6)
    threats_discovered_total: int = 0
    takedowns_completed_total: int = 0
    takedowns_completed_this_month: int = 0
    average_time_to_takedown_hours: Optional[float] = None
    bad_actors_identified: int = 0
    platforms_breakdown: dict = {}
    monthly_trend: List[dict] = []


# ============================================
# AUTHORIZED SELLERS SCHEMAS (Feature 7)
# ============================================
class AuthorizedSellerCreate(BaseModel):
    domain: str
    seller_name: Optional[str] = None
    platform: Optional[str] = None
    platform_seller_id: Optional[str] = None
    relationship: str = "authorized_distributor"


class AuthorizedSellerResponse(BaseModel):
    id: str
    client_id: str
    domain: str
    seller_name: Optional[str] = None
    platform: Optional[str] = None
    platform_seller_id: Optional[str] = None
    relationship: str
    added_by: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# NOTIFICATION SETTINGS SCHEMAS (Feature 8)
# ============================================
class NotificationSettingsUpdate(BaseModel):
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    notification_prefs: Optional[dict] = None


class NotificationSettingsResponse(BaseModel):
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    notification_prefs: dict = {}


# ============================================
# FREE SCAN SCHEMAS (Feature 4)
# ============================================
class FreeScanResult(BaseModel):
    platform: str
    country: str
    similarity_score: float
    thumbnail_url: Optional[str] = None
    domain_hint: str


class FreeScanResponse(BaseModel):
    total_matches_found: int
    high_confidence_matches: int
    results: List[FreeScanResult]
    email_captured: bool
    cta_message: str


# ============================================
# VERIFICATION SCHEMAS
# ============================================
class VerifyThreatRequest(BaseModel):
    asset_id: str
    candidate_image_url: AnyHttpUrl
    candidate_listing_url: AnyHttpUrl
    host_domain: str
    seller_name: Optional[str] = None
    listing_title: Optional[str] = None
    listing_price: Optional[float] = Field(default=None, ge=0)

    @field_validator("candidate_image_url", "candidate_listing_url", mode="before")
    @classmethod
    def validate_no_private_ip(cls, v: str) -> str:
        import ipaddress
        from urllib.parse import urlparse
        host = urlparse(str(v)).hostname or ""
        try:
            addr = ipaddress.ip_address(host)
            if addr.is_private or addr.is_loopback or addr.is_link_local:
                raise ValueError(f"URL must not point to a private or loopback address: {host}")
        except ValueError as exc:
            if "private" in str(exc) or "loopback" in str(exc):
                raise
        return v


class VerifyThreatResponse(BaseModel):
    is_threat: bool
    similarity_score: float
    threat_id: Optional[str] = None
