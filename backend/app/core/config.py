"""SniperIP Backend - Core Configuration"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    supabase_db_url: str = ""
    supabase_storage_bucket: str = "assets"
    evidence_storage_bucket: str = "evidence-locker"
    loa_storage_bucket: str = "legal-documents"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_starter_price_id: str = ""
    stripe_growth_price_id: str = ""
    stripe_agency_price_id: str = ""

    # SerpApi
    serpapi_key: str = ""
    serpapi_engine: str = "google_lens"

    # Resend
    resend_api_key: str = ""

    # Slack
    slack_webhook_url: str = ""
    notification_from_email: str = "SniperIP <noreply@sniperip.com>"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ZenRows
    zenrows_api_key: str = ""

    # HuggingFace
    huggingface_api_token: str = ""
    huggingface_embedding_model: str = "google/siglip-base-patch16-224"

    # Verification
    similarity_threshold: float = 0.95

    # Automation
    two_captcha_api_key: str = ""
    shopify_dmca_form_url: str = "https://www.shopify.com/legal/report-aup-violation"
    playwright_headless: bool = True

    # App
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    admin_emails: str = "admin@sniperip.com"

    # Tier limits
    starter_threat_limit: int = 50
    growth_threat_limit: int = 500
    agency_threat_limit: int = 5000

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
