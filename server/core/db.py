"""
FormNest — Async Database Engine & Session

Mirrors TREEEX-WBSP core/db.py pattern.
Uses SQLAlchemy 2.0 async with asyncpg driver.
Engine is initialised lazily on first use so that importing server modules
never fails when DATABASE_URL is absent (e.g. during tests or CLI tooling).
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine

from server.core.config import settings

logger = logging.getLogger("formnest.db")

# Lazy singletons — populated by _get_engine() on first call.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_database_url() -> str:
    """
    Return a validated async-compatible database URL.

    Converts ``postgresql://`` → ``postgresql+asyncpg://`` and strips any
    ``sslmode=`` query parameter that asyncpg does not support.

    Raises ``RuntimeError`` if DATABASE_URL is not configured.
    """
    url = settings.DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Set DATABASE_URL (or POSTGRES_* vars) in your .env file."
        )

    # Ensure we use asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # asyncpg does not support sslmode= in the URL; strip it
    if "sslmode=" in url:
        url = re.sub(r"([?&])sslmode=[^&]*(&|$)", r"\1", url)
        url = url.rstrip("?&")

    return url


def _get_engine() -> AsyncEngine:
    """Return the singleton async engine, creating it on first call."""
    global _engine, _session_factory
    if _engine is None:
        # SSL: required for managed cloud DBs (Neon, Supabase, Azure).
        # Set DB_REQUIRE_SSL=false in your .env for local dev without SSL.
        connect_args: dict = {"ssl": settings.DB_REQUIRE_SSL} if settings.DB_REQUIRE_SSL else {}

        _engine = create_async_engine(
            _build_database_url(),
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=settings.DEBUG and settings.ENV == "development",
            connect_args=connect_args,
        )
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _engine


# Convenience property for code that still references ``engine`` directly
# (e.g. the /ready health-check endpoint).
class _LazyEngine:
    """Proxy that forwards attribute access to the lazily-created engine."""

    def __getattr__(self, name: str) -> object:
        return getattr(_get_engine(), name)

    def begin(self):  # type: ignore[override]
        """Return an async context manager for a connection, matching AsyncEngine.begin()."""
        return _get_engine().begin()

    async def dispose(self) -> None:
        if _engine is not None:
            await _engine.dispose()


engine: AsyncEngine = _LazyEngine()  # type: ignore[assignment]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    _get_engine()  # ensure engine + factory are initialised
    assert _session_factory is not None
    async with _session_factory() as session:
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
        from sqlalchemy import text as sql_text

        async with _get_engine().begin() as conn:
            await conn.execute(sql_text("SELECT 1"))
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise


async def close_db() -> None:
    """Dispose of the engine connection pool."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
    logger.info("Database connection pool closed")
