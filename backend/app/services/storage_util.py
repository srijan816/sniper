"""Storage helpers for Supabase Storage public URLs.

The backend talks to Supabase over an internal address (e.g. http://kong:8000),
so ``storage.get_public_url`` returns URLs rooted at that internal host. Those
URLs get persisted (asset/thumbnail/evidence/LOA) and rendered in the browser,
which cannot resolve the internal host. ``public_url`` normalises the result and
rewrites the internal base to the browser-facing base (``SUPABASE_PUBLIC_URL``).
"""
from __future__ import annotations

from app.core.config import get_settings


def _unwrap(raw, fallback: str) -> str:
    if isinstance(raw, dict):
        return raw.get("publicUrl") or raw.get("public_url") or fallback
    return str(raw)


def to_public_url(url: str) -> str:
    """Rewrite an internal Supabase base in ``url`` to the public origin."""
    settings = get_settings()
    internal = (settings.supabase_url or "").rstrip("/")
    public = (settings.supabase_public_url or "").rstrip("/")
    if internal and public and internal != public and url.startswith(internal):
        return public + url[len(internal):]
    return url


def public_url(storage, path: str) -> str:
    """Upload-agnostic: get a browser-loadable public URL for ``path``."""
    return to_public_url(_unwrap(storage.get_public_url(path), path))
