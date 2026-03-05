"""
FormNest — Application Settings

Loads configuration from environment variables using pydantic-settings.
Pattern mirrors TREEEX-WBSP core/config.py for merger compatibility.
"""

import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> str:
    """Find .env file by checking multiple possible locations."""
    this_file_dir = Path(__file__).resolve().parent

    possible_paths = [
        Path.cwd() / ".env",
        this_file_dir / ".env",
        this_file_dir.parent / ".env",
        this_file_dir.parent.parent / ".env",
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    return ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Server ---
    ENV: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    CLIENT_URL: str = "http://localhost:5173"
    API_URL: str = "http://localhost:8001"  # Public-facing API base URL

    # --- Database ---
    DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int | None = None
    POSTGRES_DB: str | None = None

    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if self.DATABASE_URL is None and all(
            [
                self.POSTGRES_USER,
                self.POSTGRES_PASSWORD,
                self.POSTGRES_HOST,
                self.POSTGRES_PORT,
                self.POSTGRES_DB,
            ]
        ):
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    # Database pool
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    # Set to True for managed cloud databases (Neon, Supabase, Azure, etc.)
    # Leave False for local development with a plain PostgreSQL container.
    DB_REQUIRE_SSL: bool = False

    # --- Redis ---
    REDIS_URL: str | None = None
    REDIS_POOL_SIZE: int = 50

    # --- Supabase (shared with TREEEX-WBSP) ---
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None
    SUPABASE_PUBLISHABLE_KEY: str | None = None
    SUPABASE_SECRET_KEY: str | None = None
    SUPABASE_WEBHOOK_SECRET: str | None = None

    # Legacy keys (backward compatibility)
    LEGACY_SUPABASE_PUBLISHABLE_KEY: str | None = None
    LEGACY_SUPABASE_SECRET_KEY: str | None = None

    @model_validator(mode="after")
    def consolidate_supabase_keys(self) -> "Settings":
        """
        Consolidate Supabase keys with fallback.
        Same logic as TREEEX-WBSP for shared auth compatibility.
        """
        if not self.SUPABASE_KEY:
            self.SUPABASE_KEY = (
                self.SUPABASE_PUBLISHABLE_KEY or self.LEGACY_SUPABASE_PUBLISHABLE_KEY
            )

        if (not self.SUPABASE_SECRET_KEY or self.SUPABASE_SECRET_KEY.startswith("sb_")) and self.LEGACY_SUPABASE_SECRET_KEY:
            self.SUPABASE_SECRET_KEY = self.LEGACY_SUPABASE_SECRET_KEY

        return self

    # --- Security ---
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 1 week

    # --- Email (Resend) ---
    RESEND_API_KEY: str | None = None
    FROM_EMAIL: str = "noreply@formnest.in"

    # --- Spam Protection ---
    HCAPTCHA_SECRET: str | None = None

    # --- Cloudflare R2 (Media Storage) ---
    R2_ACCOUNT_ID: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET_NAME: str = "formnest-media"
    R2_PUBLIC_URL: str | None = None

    # --- Monitoring ---
    SENTRY_DSN: str | None = None
    LOGFIRE_TOKEN: str | None = None
    DB_SLOW_QUERY_THRESHOLD: float = 300.0  # ms

    # --- Development Tunnel ---
    DEVTUNNEL_NAME: str = "formnest-webhook"
    DEVTUNNEL_URL: str | None = None

    def validate_production_config(self) -> list[str]:
        """
        Validate critical configuration for production deployment.
        Returns list of missing/invalid configuration items.
        """
        errors = []

        if not self.DATABASE_URL and not self.POSTGRES_HOST:
            errors.append("DATABASE_URL or POSTGRES_* vars must be set")

        if not self.REDIS_URL:
            errors.append("REDIS_URL must be set")

        if not self.SUPABASE_URL:
            errors.append("SUPABASE_URL must be set")
        if not self.SUPABASE_KEY:
            errors.append("SUPABASE_KEY must be set")

        if not self.SECRET_KEY:
            errors.append("SECRET_KEY must be set for token signing")

        if not self.RESEND_API_KEY:
            errors.append("RESEND_API_KEY must be set for email notifications")

        if self.DEBUG and self.ENV == "production":
            errors.append("DEBUG must be False in production")

        return errors


# Singleton instance
settings = Settings()

# Validate configuration on import if in production
if settings.ENV == "production":
    config_errors = settings.validate_production_config()
    if config_errors:
        raise RuntimeError(
            "Production configuration validation failed:\n"
            + "\n".join(f"  - {error}" for error in config_errors)
        )


# Debug helper
if __name__ == "__main__":
    print("=" * 50)
    print("FORMNEST CONFIG DEBUG INFO")
    print("=" * 50)
    print(f"Working directory: {os.getcwd()}")
    print(f"Config file location: {Path(__file__).resolve()}")
    print(f"Resolved .env path: {find_env_file()}")
    print("-" * 50)
    print(f"ENV: {settings.ENV}")
    print(f"PORT: {settings.PORT}")
    print(f"DATABASE_URL loaded: {settings.DATABASE_URL is not None}")
    print(f"SUPABASE_URL: {settings.SUPABASE_URL}")
    print(f"SUPABASE_KEY loaded: {settings.SUPABASE_KEY is not None}")
    print(f"REDIS_URL: {settings.REDIS_URL}")
    print(f"RESEND_API_KEY loaded: {settings.RESEND_API_KEY is not None}")
    print("=" * 50)
