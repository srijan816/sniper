"""Shared SlowAPI limiter — single instance wired to app.state.limiter."""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter


def get_real_ip(request: Request) -> str:
    """Extract the real client IP, accounting for Cloudflare, Nginx, and AWS ALB proxies."""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_real_ip, default_limits=["1000/minute"])
