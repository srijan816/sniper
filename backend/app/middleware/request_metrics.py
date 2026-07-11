"""HTTP request metrics middleware."""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.metrics import record_http_request


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not get_settings().prometheus_enabled:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        record_http_request(
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response
