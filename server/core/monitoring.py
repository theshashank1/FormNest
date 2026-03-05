"""
FormNest — Monitoring & Observability

Sentry error tracking + Logfire observability.
Mirrors TREEEX-WBSP core/monitoring.py pattern.
"""

from __future__ import annotations

import logging
from typing import Any

from server.core.config import settings

logger = logging.getLogger("formnest.monitoring")


def init_sentry() -> None:
    """Initialize Sentry error tracking if DSN is configured."""
    if not settings.SENTRY_DSN:
        logger.info("Sentry DSN not configured — error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=1.0 if settings.ENV == "development" else 0.1,
            send_default_pii=(settings.ENV == "development"),
            environment=settings.ENV,
        )
        logger.info("✅ Sentry initialized")
    except ImportError:
        logger.warning("sentry-sdk not installed — error tracking disabled")


def init_logfire() -> None:
    """Initialize Logfire observability if token is configured."""
    if not settings.LOGFIRE_TOKEN:
        logger.info("Logfire token not configured — observability disabled")
        return

    try:
        import logfire

        logfire.configure(token=settings.LOGFIRE_TOKEN)
        logger.info("✅ Logfire initialized")
    except ImportError:
        logger.warning("logfire not installed — observability disabled")


def log_event(
    event: str,
    *,
    level: str = "info",
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Structured event logging.

    Args:
        event: Event name (e.g., "submission.created", "form.ddl_executed")
        level: Log level (debug, info, warning, error)
        extra: Additional context data
    """
    log_func = getattr(logger, level, logger.info)
    msg = f"[{event}]"
    if extra:
        msg += f" {extra}"
    log_func(msg)


def log_exception(
    event: str,
    exc: Exception,
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Log an exception with structured context.

    Args:
        event: Event name
        exc: The exception
        extra: Additional context data
    """
    context = {"error": str(exc), "error_type": type(exc).__name__}
    if extra:
        context.update(extra)
    logger.error(f"[{event}] {context}", exc_info=True)

    # Also send to Sentry if available
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except ImportError:
        pass
