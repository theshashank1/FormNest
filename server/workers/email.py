"""
FormNest — Email Worker

Sends transactional emails via Resend.com.
Phase 0: Skeleton — activated in Phase 1.
"""

from __future__ import annotations

import logging
from typing import Any

from server.core.redis import QUEUE_EMAILS, dequeue

logger = logging.getLogger("formnest.workers.email")


async def process_email_job(data: dict[str, Any]) -> None:
    """Process a single email job."""
    logger.info(f"Sending email: type={data.get('email_type')} to={data.get('recipient')}")

    # TODO Phase 1: Resend.com integration
    # - Load email template
    # - Render with data
    # - Send via Resend API
    # - Log to email_logs table
    # - Retry on failure (3 attempts)

    logger.info("Email sent (stub)")


async def run_email_worker() -> None:
    """Main worker loop."""
    logger.info(f"📧 Email worker started (queue: {QUEUE_EMAILS})")

    while True:
        try:
            job = await dequeue(QUEUE_EMAILS, timeout=5)
            if job:
                await process_email_job(job)
        except Exception as e:
            logger.error(f"Email worker error: {e}", exc_info=True)
