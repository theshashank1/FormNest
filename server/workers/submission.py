"""
FormNest — Submission Worker

Processes form submissions from the Redis queue.
Phase 0: Skeleton — full pipeline activated in Phase 1.
"""

from __future__ import annotations

import logging
from typing import Any

from server.core.redis import QUEUE_SUBMISSIONS, dequeue

logger = logging.getLogger("formnest.workers.submission")


async def process_submission_job(data: dict[str, Any]) -> None:
    """
    Process a single submission job from the queue.

    Pipeline:
    1. spam_check()      → honeypot, IP rate limit, pattern scoring
    2. validate_schema() → check required fields, types, max lengths
    3. enrich_meta()     → source URL, referrer, device type, UTM params
    4. db_insert()       → insert into dynamic table + index
    5. analytics_bump()  → increment submission_count, daily snapshot
    6. notify_email()    → LPUSH queue:emails (non-blocking)
    7. fire_webhooks()   → LPUSH queue:webhooks for each configured hook
    8. partial_cleanup() → delete any partial save session for this contact
    """
    logger.info(f"Processing submission: {data.get('submission_id', 'unknown')}")

    # Phase 0: Submissions are processed synchronously in the API
    # Phase 1: This worker will handle async processing from the queue
    # TODO: Implement full async pipeline

    logger.info(f"Submission processed: {data.get('submission_id', 'unknown')}")


async def run_submission_worker() -> None:
    """Main worker loop — dequeue and process submissions."""
    logger.info(f"🔄 Submission worker started (queue: {QUEUE_SUBMISSIONS})")

    while True:
        try:
            job = await dequeue(QUEUE_SUBMISSIONS, timeout=5)
            if job:
                await process_submission_job(job)
        except Exception as e:
            logger.error(f"Submission worker error: {e}", exc_info=True)
