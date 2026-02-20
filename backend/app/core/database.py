"""Supabase client initialization"""
from supabase import create_client, Client
from app.core.config import get_settings


def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        # Return a mock-like None for development without Supabase
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_admin() -> Client:
    """Admin client with service role key - bypasses RLS"""
    return get_supabase_client()
