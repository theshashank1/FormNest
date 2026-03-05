"""
FormNest — Async Database Engine & Session

Mirrors TREEEX-WBSP core/db.py pattern.
Uses SQLAlchemy 2.0 async with asyncpg driver.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.core.config import settings

logger = logging.getLogger("formnest.db")


def _get_database_url() -> str:
    """Get database URL, ensuring asyncpg driver is used and stripping incompatible params."""
    url = settings.DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")

    # Ensure we use asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # asyncpg doesn't support sslmode= in the URL; strip it if present
    if "sslmode=" in url:
        import re
        url = re.sub(r'([?&])sslmode=[^&]*(&|$)', r'\1', url)
        url = url.rstrip('?&')

    return url


# Async engine — created once on module import
# Azure PostgreSQL often requires SSL.
engine = create_async_engine(
    _get_database_url(),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG and settings.ENV == "development",
    connect_args={"ssl": True},
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Verify database connection on startup."""
    try:
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise


async def close_db() -> None:
    """Dispose of the engine connection pool."""
    await engine.dispose()
    logger.info("Database connection pool closed")
