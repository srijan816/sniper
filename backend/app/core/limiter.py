"""Shared SlowAPI limiter — single instance wired to app.state.limiter."""
from __future__ import annotations

import ipaddress

from fastapi import Request
from slowapi import Limiter

# Proxy-set client-IP headers are only honored when the *immediate* peer is a
# trusted hop (our Caddy/nginx live on private docker/host ranges; Cloudflare
# fronts the edge). An attacker who reaches the app from an untrusted address
# cannot spoof these headers to dodge per-IP limits — we use their real peer IP.
_TRUSTED_NETS = [
    ipaddress.ip_network(c) for c in (
        "127.0.0.0/8", "::1/128",
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7",
    )
]


def _peer_trusted(host: str | None) -> bool:
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(ip in net for net in _TRUSTED_NETS)


def get_real_ip(request: Request) -> str:
    """Real client IP. Forwarded headers are trusted only from a trusted peer."""
    peer = request.client.host if request.client else None
    if _peer_trusted(peer):
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    return peer or "unknown"


limiter = Limiter(key_func=get_real_ip, default_limits=["1000/minute"])
