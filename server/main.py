"""
FormNest — Main Application Entry Point

Configures FastAPI application, middleware, lifecycle events, and routers.
Pattern mirrors TREEEX-WBSP server/main.py.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from server.api import api_router, public_router
from server.core.config import settings
from server.core.monitoring import init_logfire, init_sentry, log_exception
from server.exceptions import FormNestBaseError

# =============================================================================
# Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application startup and shutdown events."""
    # Startup
    from server.core.db import init_db
    from server.core.redis import init_redis

    await init_db()
    await init_redis()
    init_sentry()
    init_logfire()

    yield

    # Shutdown
    from server.core.db import close_db
    from server.core.redis import close_redis

    await close_redis()
    await close_db()


# =============================================================================
# App Instance
# =============================================================================

app = FastAPI(
    title="FormNest API",
    description="Serverless-experience SaaS — embed forms, collect leads, zero backend required",
    version="0.1.0",
    lifespan=lifespan,
)


# =============================================================================
# Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.CLIENT_URL,
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Next.js blog
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Global Exception Handlers
# =============================================================================

@app.exception_handler(FormNestBaseError)
async def formnest_exception_handler(request: Request, exc: FormNestBaseError) -> JSONResponse:
    """Handle custom FormNest exceptions with standardised response format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with detailed field information."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "unknown"),
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "detail": "Request validation failed",
            "errors": errors,
        },
    )


@app.exception_handler(IntegrityError)
async def database_integrity_exception_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle database integrity constraint violations."""
    log_exception("db.integrity_error", exc)

    detail = "A database constraint was violated"
    if "unique" in str(exc).lower():
        detail = "A record with this data already exists"

    return JSONResponse(
        status_code=409,
        content={
            "error": "CONFLICT",
            "detail": detail,
        },
    )


@app.exception_handler(OperationalError)
async def database_operational_exception_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """Handle database operational errors."""
    log_exception("db.operational_error", exc)
    return JSONResponse(
        status_code=503,
        content={
            "error": "SERVICE_UNAVAILABLE",
            "detail": "Database temporarily unavailable",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    log_exception("unhandled_error", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "detail": "An unexpected error occurred" if settings.ENV == "production"
                      else str(exc),
        },
    )


# =============================================================================
# Routers
# =============================================================================

# Authenticated API routes
app.include_router(api_router)

# Public routes (submit, standalone forms)
app.include_router(public_router)


# =============================================================================
# Health Checks
# =============================================================================

@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    """Health check endpoint. Returns 200 if running."""
    return {
        "status": "ok",
        "service": "formnest-api",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/ready", tags=["Health"])
async def readiness_check() -> JSONResponse:
    """Readiness check — verifies DB and Redis connectivity."""
    checks = {"api": "ok"}

    try:
        from sqlalchemy import text as sql_text

        from server.core.db import engine
        async with engine.begin() as conn:
            await conn.execute(sql_text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    try:
        from server.core.redis import get_redis
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )
