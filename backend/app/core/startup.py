"""Production startup validation — fail fast on missing critical config."""
from __future__ import annotations

import logging
import sys

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

REQUIRED_PRODUCTION = (
    "supabase_url",
    "supabase_service_role_key",
    "redis_url",
)

RECOMMENDED_PRODUCTION = (
    "serpapi_key",
    "huggingface_api_token",
    "resend_api_key",
)


def validate_startup(*, settings: Settings | None = None, strict: bool | None = None) -> list[str]:
    """
    Validate environment configuration at startup.
    Returns list of warnings; raises SystemExit in strict production mode on errors.
    """
    settings = settings or get_settings()
    strict = strict if strict is not None else settings.environment == "production"
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_PRODUCTION:
        if not getattr(settings, key, ""):
            errors.append(f"Missing required setting: {key.upper()}")

    for key in RECOMMENDED_PRODUCTION:
        if not getattr(settings, key, ""):
            warnings.append(f"Missing recommended setting: {key.upper()}")

    if settings.environment == "production":
        if settings.takedown_test_mode_no_submit:
            warnings.append(
                "TAKEDOWN_TEST_MODE_NO_SUBMIT=true — takedowns will NOT be submitted (intended for staging only)"
            )
        if not settings.metrics_auth_token:
            warnings.append("METRICS_AUTH_TOKEN unset — /api/metrics will reject unauthenticated scrapes in production")
        if not settings.huggingface_inference_endpoint_url:
            warnings.append(
                "HUGGINGFACE_INFERENCE_ENDPOINT_URL unset — vision embeddings may use shared HF API (not recommended for prod)"
            )
        if settings.huggingface_allow_openai_fallback:
            warnings.append("HUGGINGFACE_ALLOW_OPENAI_FALLBACK=true — OpenAI fallback enabled in production")

    for msg in warnings:
        logger.warning("Startup validation: %s", msg)

    if errors:
        for msg in errors:
            logger.error("Startup validation: %s", msg)
        if strict:
            raise SystemExit(f"Startup validation failed: {'; '.join(errors)}")

    return warnings


def run_prod_check(settings: Settings | None = None) -> dict:
    """Non-fatal readiness report for scripts/CI."""
    settings = settings or get_settings()
    report: dict = {
        "environment": settings.environment,
        "errors": [],
        "warnings": [],
        "checks": {},
    }

    for key in REQUIRED_PRODUCTION:
        ok = bool(getattr(settings, key, ""))
        report["checks"][key] = ok
        if not ok:
            report["errors"].append(f"Missing {key}")

    for key in RECOMMENDED_PRODUCTION:
        ok = bool(getattr(settings, key, ""))
        report["checks"][key] = ok
        if not ok:
            report["warnings"].append(f"Missing {key}")

    report["ok"] = len(report["errors"]) == 0
    return report
