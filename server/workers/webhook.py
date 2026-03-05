"""
FormNest — Webhook Delivery Worker

Fires outbound webhooks to configured URLs on form events.
Phase 0: Skeleton — activated in Phase 1.
"""

from __future__ import annotations

import logging
from typing import Any

from server.core.redis import QUEUE_WEBHOOKS, dequeue

logger = logging.getLogger("formnest.workers.webhook")


async def process_webhook_job(data: dict[str, Any]) -> None:
    """Process a single webhook delivery job."""
    logger.info(f"Delivering webhook: hook_id={data.get('hook_id')}")

    # TODO Phase 1: Full webhook delivery
    # - Load hook config (url, secret, events, headers)
    # - Build payload + HMAC-SHA256 signature
    # - POST to target URL (5s timeout)
    # - Log to webhook_delivery_logs
    # - Retry on failure (3 attempts: 10s, 1min, 5min)

    logger.info("Webhook delivered (stub)")


async def run_webhook_worker() -> None:
    """Main worker loop."""
    logger.info(f"🔗 Webhook worker started (queue: {QUEUE_WEBHOOKS})")

    while True:
        try:
            job = await dequeue(QUEUE_WEBHOOKS, timeout=5)
            if job:
                await process_webhook_job(job)
        except Exception as e:
            logger.error(f"Webhook worker error: {e}", exc_info=True)
