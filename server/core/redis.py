"""
FormNest — Redis Client & Queue Helpers

Queue keys are prefixed with 'fn:' to avoid collision with WBSP's 'queue:*'
at merger time. Both products share the same Redis instance.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from server.core.config import settings

logger = logging.getLogger("formnest.redis")

# Queue key prefix — separates FormNest keys from WBSP keys
QUEUE_PREFIX = "fn:"

# Well-known queue names
QUEUE_SUBMISSIONS = f"{QUEUE_PREFIX}queue:submissions"
QUEUE_EMAILS = f"{QUEUE_PREFIX}queue:emails"
QUEUE_WEBHOOKS = f"{QUEUE_PREFIX}queue:webhooks"
QUEUE_OG_IMAGES = f"{QUEUE_PREFIX}queue:og_images"

# Cache key prefix
CACHE_PREFIX = f"{QUEUE_PREFIX}cache:"

# Rate limit prefix
RATE_LIMIT_PREFIX = f"{QUEUE_PREFIX}rate:"

# Partial save (ghost lead) prefix
PARTIAL_PREFIX = f"{QUEUE_PREFIX}partial:"

# Redis connection pool (initialized on startup)
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get the Redis client instance."""
    global _redis_pool
    if _redis_pool is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_pool


async def init_redis() -> None:
    """Initialize Redis connection pool."""
    global _redis_pool
    if not settings.REDIS_URL:
        logger.warning("⚠️  REDIS_URL not set — Redis features disabled")
        return

    _redis_pool = aioredis.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_POOL_SIZE,
        decode_responses=True,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )

    # Verify connection
    try:
        await _redis_pool.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        _redis_pool = None
        raise


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Redis connection pool closed")


# =============================================================================
# Queue Operations
# =============================================================================


async def enqueue(queue_name: str, data: dict[str, Any]) -> None:
    """
    Push a job onto a Redis queue.

    Args:
        queue_name: The queue key name (e.g., QUEUE_SUBMISSIONS)
        data: JSON-serializable dict to enqueue
    """
    redis = await get_redis()
    payload = json.dumps(data, default=str)
    await redis.lpush(queue_name, payload)


async def dequeue(queue_name: str, timeout: int = 0) -> dict[str, Any] | None:
    """
    Pop a job from a Redis queue (blocking).

    Args:
        queue_name: The queue key name
        timeout: Block for this many seconds (0 = block indefinitely)

    Returns:
        Parsed dict or None if timeout reached
    """
    redis = await get_redis()
    result = await redis.brpop(queue_name, timeout=timeout)
    if result:
        _, payload = result
        return json.loads(payload)
    return None


async def queue_length(queue_name: str) -> int:
    """Get the number of items in a queue."""
    redis = await get_redis()
    return await redis.llen(queue_name)


# =============================================================================
# Cache Operations
# =============================================================================


async def cache_get(key: str) -> str | None:
    """Get a cached value."""
    redis = await get_redis()
    return await redis.get(f"{CACHE_PREFIX}{key}")


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    """Set a cached value with TTL (default 5 minutes)."""
    redis = await get_redis()
    await redis.setex(f"{CACHE_PREFIX}{key}", ttl, value)


async def cache_delete(key: str) -> None:
    """Delete a cached value."""
    redis = await get_redis()
    await redis.delete(f"{CACHE_PREFIX}{key}")


# =============================================================================
# Rate Limiting
# =============================================================================


async def check_rate_limit(
    identifier: str,
    limit: int = 5,
    window_seconds: int = 60,
) -> tuple[bool, int]:
    """
    Sliding window rate limiter.

    Args:
        identifier: Unique key (e.g., "ip:form_key")
        limit: Max requests in window
        window_seconds: Window duration

    Returns:
        (is_allowed, current_count)
    """
    redis = await get_redis()
    key = f"{RATE_LIMIT_PREFIX}{identifier}"

    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_seconds)

    return current <= limit, current


# =============================================================================
# Pub/Sub (for realtime dashboard updates)
# =============================================================================


async def publish(channel: str, data: dict[str, Any]) -> None:
    """Publish a message to a Redis pub/sub channel."""
    redis = await get_redis()
    payload = json.dumps(data, default=str)
    await redis.publish(f"{QUEUE_PREFIX}{channel}", payload)
