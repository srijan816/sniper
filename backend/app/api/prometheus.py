"""Prometheus scrape endpoint."""
from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.metrics import metrics_payload

router = APIRouter()


def _authorize_metrics(request: Request) -> Response | None:
    settings = get_settings()
    token = (settings.metrics_auth_token or "").strip()
    # No token configured => deny in every environment. This avoids exposing
    # telemetry when ENVIRONMENT is left at its "development" default. To scrape
    # locally, set METRICS_AUTH_TOKEN (it is enforced everywhere when present).
    if not token:
        return Response(status_code=401, content="METRICS_AUTH_TOKEN not configured")
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {token}":
        return Response(status_code=401, content="Unauthorized")
    return None


@router.get("/metrics")
async def prometheus_metrics(request: Request):
    """Expose Prometheus metrics (Bearer token required in production)."""
    if not get_settings().prometheus_enabled:
        return Response(status_code=404, content="Metrics disabled")
    denied = _authorize_metrics(request)
    if denied is not None:
        return denied
    return Response(content=metrics_payload(), media_type="text/plain; version=0.0.4; charset=utf-8")
