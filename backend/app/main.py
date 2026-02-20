"""SniperIP Backend - FastAPI Main Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.assets import router as assets_router
from app.api.threats import router as threats_router
from app.api.verify import router as verify_router
from app.api.takedown import router as takedown_router
from app.api.admin import router as admin_router
from app.api.webhooks import router as webhooks_router
from app.api.clients import router as clients_router

app = FastAPI(
    title="SniperIP API",
    description="IP Protection SaaS Backend — Discover, verify, and take down counterfeit listings.",
    version="1.0.0",
)

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
app.include_router(clients_router, prefix="/api/clients", tags=["Clients"])
app.include_router(assets_router, prefix="/api/assets", tags=["Assets"])
app.include_router(threats_router, prefix="/api/threats", tags=["Threats"])
app.include_router(verify_router, prefix="/api", tags=["Verification"])
app.include_router(takedown_router, prefix="/api/takedown", tags=["Takedown"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["Webhooks"])
