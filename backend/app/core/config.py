"""SniperIP Backend - Core Configuration"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    # Browser-facing base used to build public storage URLs. When the backend
    # talks to Supabase over an internal address (e.g. http://kong:8000), set
    # this to the public origin (e.g. https://sniperip.com) so stored image
    # URLs are loadable from the browser. Falls back to supabase_url when unset.
    supabase_public_url: str = ""
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

    # SerpApi (optional paid discovery — leave blank to use free SearXNG instead)
    serpapi_key: str = ""
    serpapi_engine: str = "google_lens"

    # SearXNG (free self-hosted discovery; reuses the shared app2 SearXNG)
    searxng_url: str = "http://searxng:8080"
    searxng_engines: str = "bing"            # web engines that work without a proxy
    searxng_image_engines: str = "bing images"
    discovery_enable_searxng: bool = True
    # Marketplaces to target via `site:` web search (comma-separated hosts)
    discovery_marketplaces: str = "ebay.com,aliexpress.com,etsy.com,walmart.com,dhgate.com,poshmark.com"

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

    # OpenAI (fallback embedding backend)
    openai_api_key: str = ""
    huggingface_embedding_model: str = "google/siglip-so400m-patch14-384"
    huggingface_embedding_backend: str = "auto"  # local | endpoint | shared | auto | openai
    huggingface_inference_endpoint_url: str = ""
    huggingface_inference_endpoint_token: str = ""
    huggingface_allow_shared_fallback: bool = True
    huggingface_allow_openai_fallback: bool = False
    embedding_request_retries: int = 3
    embedding_dimension: int = 1152
    embedding_input_size: int = 384

    # DINOv2 structural similarity (ensemble verification)
    dinov2_enabled: bool = True
    dinov2_model: str = "facebook/dinov2-large"
    dinov2_backend: str = "shared"  # shared | local

    # MiniMax M3 (threat explanations, intelligence)
    minimax_api_key: str = ""
    minimax_model: str = "MiniMax-M3"

    # AI-Q deep research (pipeline intelligence)
    aiq_base_url: str = "https://app2.sniperip.com"
    aiq_api_token: str = ""
    research_poll_interval_seconds: int = 120

    # Verification ensemble weights — research-backed (AI-Q vision-ensemble report)
    similarity_weight_siglip: float = 0.55
    similarity_weight_dinov2: float = 0.40
    similarity_weight_phash: float = 0.05

    # Verification
    similarity_threshold: float = 0.90
    phash_distance_threshold: int = 6

    # Discovery sources
    discovery_enable_shopping_search: bool = True
    discovery_enable_bing_reverse: bool = True

    # Automation
    two_captcha_api_key: str = ""
    shopify_dmca_form_url: str = "https://www.shopify.com/legal/report-aup-violation"
    playwright_headless: bool = True
    playwright_stealth_enabled: bool = True
    playwright_proxy_server: str = ""
    playwright_proxy_username: str = ""
    playwright_proxy_password: str = ""
    playwright_proxy_bypass: str = ""
    playwright_proxy_pool: str = ""  # comma-separated: server|username|password|bypass
    playwright_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # Discovery pacing
    discovery_tick_interval_seconds: int = 900
    discovery_client_spacing_seconds: int = 30

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
    cors_origins: str = "http://localhost:3000,https://sniperip.com"
    public_host: str = ""
    environment: str = "development"  # development | staging | production
    app_version: str = "1.0.0"

    # Observability
    log_level: str = "INFO"
    log_json: bool = False
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    prometheus_enabled: bool = True
    metrics_auth_token: str = ""

    # Tier limits
    starter_threat_limit: int = 50
    growth_threat_limit: int = 500
    agency_threat_limit: int = 5000

    # Test Mode
    takedown_test_mode_no_submit: bool = False

    # Discovery performance — skip full DINOv2 ensemble when quick score is far below threshold
    discovery_fast_reject_margin: float = 0.12

    # Stripe — only allow unsigned webhooks when explicitly enabled (local dev)
    stripe_webhook_allow_unsigned: bool = False

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
