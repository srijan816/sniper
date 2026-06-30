"""SniperIP Backend - FastAPI Main Application"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.logging_config import configure_logging, init_sentry
from app.core.startup import validate_startup
from app.middleware.request_metrics import RequestMetricsMiddleware

configure_logging()
init_sentry()


def _cors_origins() -> list[str]:
    settings = get_settings()
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if settings.frontend_url and settings.frontend_url not in origins:
        origins.append(settings.frontend_url)
    if settings.public_host:
        for scheme in ("http", "https"):
            origin = f"{scheme}://{settings.public_host}"
            if origin not in origins:
                origins.append(origin)
    return origins


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
from app.api.counterfeits import router as counterfeits_router
from app.api.prometheus import router as prometheus_router



# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
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
app.include_router(counterfeits_router, prefix="/api/counterfeits", tags=["Counterfeits"])
