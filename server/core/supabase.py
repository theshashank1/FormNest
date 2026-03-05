"""
FormNest — Supabase Client

Shared Supabase project with TREEEX-WBSP — same user UUIDs.
"""

from __future__ import annotations

import logging

from supabase import Client, create_client

from server.core.config import settings

logger = logging.getLogger("formnest.supabase")

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Get or create the Supabase client singleton.

    Uses the same Supabase project as TREEEX-WBSP for shared auth.
    """
    global _supabase_client

    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set. "
                "This should be the same Supabase project as TREEEX-WBSP."
            )

        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )
        logger.info("✅ Supabase client initialized (shared with WBSP)")

    return _supabase_client


def get_supabase_admin_client() -> Client:
    """
    Get a Supabase client with service_role key for admin operations.

    Required for operations like listing users, managing auth, etc.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SECRET_KEY must be set for admin operations."
        )

    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY,
    )
