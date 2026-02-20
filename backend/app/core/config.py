"""SniperIP Backend - Core Configuration"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_starter_price_id: str = ""
    stripe_growth_price_id: str = ""
    stripe_agency_price_id: str = ""

    # SerpApi
    serpapi_key: str = ""

    # Resend
    resend_api_key: str = ""

    # Slack
    slack_webhook_url: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ZenRows
    zenrows_api_key: str = ""

    # HuggingFace
    huggingface_api_token: str = ""

    # App
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    admin_emails: str = "admin@sniperip.com"

    # Tier limits
    starter_threat_limit: int = 50
    growth_threat_limit: int = 500
    agency_threat_limit: int = 5000

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
