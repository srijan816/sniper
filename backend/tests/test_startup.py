"""Tests for production startup validation."""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.startup import run_prod_check, validate_startup


def test_prod_check_missing_required():
    settings = Settings(
        supabase_url="",
        supabase_service_role_key="",
        redis_url="",
    )
    report = run_prod_check(settings=settings)
    assert report["ok"] is False
    assert len(report["errors"]) >= 3


def test_validate_startup_non_strict_does_not_exit():
    settings = Settings(supabase_url="", environment="development")
    warnings = validate_startup(settings=settings, strict=False)
    assert isinstance(warnings, list)


def test_validate_startup_strict_production_raises():
    settings = Settings(
        environment="production",
        supabase_url="",
        supabase_service_role_key="",
        redis_url="",
    )
    with pytest.raises(SystemExit):
        validate_startup(settings=settings, strict=True)
