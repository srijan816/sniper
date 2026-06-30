"""Prometheus scrape endpoint."""
from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.core.metrics import metrics_payload

router = APIRouter()


@router.get("/metrics")
async def prometheus_metrics():
    """Expose Prometheus metrics for scraping (firewall in production)."""
    if not get_settings().prometheus_enabled:
        return Response(status_code=404, content="Metrics disabled")
    return Response(content=metrics_payload(), media_type="text/plain; version=0.0.4; charset=utf-8")
