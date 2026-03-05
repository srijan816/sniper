"""Supabase and Postgres client initialization."""
from contextlib import contextmanager
from typing import Optional

import psycopg
from psycopg.rows import dict_row
from supabase import create_client, Client

from app.core.config import get_settings


def get_supabase_client() -> Optional[Client]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        # Supabase-dependent routes/workers guard against an unconfigured client.
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_admin() -> Client:
    """Admin client with service role key - bypasses RLS"""
    return get_supabase_client()


@contextmanager
def get_pg_connection():
    """Raw Postgres connection for pgvector queries."""
    settings = get_settings()
    if not settings.supabase_db_url:
        raise RuntimeError("SUPABASE_DB_URL is not configured.")

    conn = psycopg.connect(settings.supabase_db_url, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_pg_transaction():
    """Transactional Postgres connection for multi-step state transitions."""
    settings = get_settings()
    if not settings.supabase_db_url:
        raise RuntimeError("SUPABASE_DB_URL is not configured.")

    conn = psycopg.connect(settings.supabase_db_url, autocommit=False, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
