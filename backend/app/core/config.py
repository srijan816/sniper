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
    zenrows_proxy_username: str = ""
    zenrows_proxy_password: str = ""
    zenrows_proxy_server: str = "http://superproxy.zenrows.com:1337"

    # HuggingFace
    huggingface_api_token: str = ""
    huggingface_embedding_model: str = "google/siglip-base-patch16-224"
    huggingface_embedding_backend: str = "local"  # local | endpoint | shared | auto
    huggingface_inference_endpoint_url: str = ""
    huggingface_inference_endpoint_token: str = ""
    huggingface_allow_shared_fallback: bool = False
    embedding_request_retries: int = 3

    # Verification
    similarity_threshold: float = 0.95
    phash_distance_threshold: int = 6

    # Automation
    two_captcha_api_key: str = ""
    shopify_dmca_form_url: str = "https://www.shopify.com/legal/report-aup-violation"
    playwright_headless: bool = True
    playwright_stealth_enabled: bool = True
    playwright_proxy_server: str = ""
    playwright_proxy_username: str = ""
    playwright_proxy_password: str = ""
    playwright_proxy_bypass: str = ""
    playwright_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # Meta / Amazon enforcement
    meta_access_token: str = ""
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_ip_report_endpoint: str = "https://graph.facebook.com/v20.0/ip_reports"
    amazon_brand_registry_endpoint: str = ""
    amazon_brand_registry_api_key: str = ""

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
