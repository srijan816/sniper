"""SniperIP Backend - FastAPI Main Application"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.logging_config import configure_logging, init_sentry
from app.core.startup import validate_startup
from app.middleware.request_metrics import RequestMetricsMiddleware

configure_logging()
init_sentry()


def get_real_ip(request: Request) -> str:
    """Extract the real client IP, accounting for Cloudflare, Nginx, and AWS ALB proxies."""
    # Cloudflare sets CF-Connecting-IP to the original client IP
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    # X-Forwarded-For may be a comma-separated chain; the first entry is the client
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # Nginx sets X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    # Fallback to direct connection
    return request.client.host if request.client else "unknown"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_startup()
    yield


app = FastAPI(
    title="SniperIP API",
    description="IP Protection SaaS Backend — Discover, verify, and take down counterfeit listings.",
    version="1.0.0",
    lifespan=lifespan,
)

limiter = Limiter(key_func=get_real_ip, default_limits=["1000/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestMetricsMiddleware)

from app.api.health import router as health_router
from app.api.assets import router as assets_router
from app.api.threats import router as threats_router
from app.api.verify import router as verify_router
from app.api.takedown import router as takedown_router
from app.api.admin import router as admin_router
from app.api.webhooks import router as webhooks_router
from app.api.clients import router as clients_router
from app.api.checkout import router as checkout_router
from app.api.scan import router as scan_router
from app.api.prometheus import router as prometheus_router



# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://sniperip.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(prometheus_router, prefix="/api", tags=["Metrics"])
app.include_router(clients_router, prefix="/api/clients", tags=["Clients"])
app.include_router(assets_router, prefix="/api/assets", tags=["Assets"])
app.include_router(threats_router, prefix="/api/threats", tags=["Threats"])
app.include_router(verify_router, prefix="/api", tags=["Verification"])
app.include_router(takedown_router, prefix="/api/takedown", tags=["Takedown"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(checkout_router, prefix="/api/checkout", tags=["Checkout"])
app.include_router(scan_router, prefix="/api/scan", tags=["Scan"])
