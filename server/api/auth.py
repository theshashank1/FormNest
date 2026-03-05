"""
FormNest — Auth API Routes

Supabase auth integration — same project as TREEEX-WBSP.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.db import get_db_session
from server.core.supabase import get_supabase_client
from server.dependencies import get_current_user
from server.exceptions import BadRequestError, UnauthorizedError
from server.models.access import User
from server.schemas.auth import (
    AuthTokenResponse,
    RefreshTokenRequest,
    SigninRequest,
    SignupRequest,
    UserResponse,
)

logger = logging.getLogger("formnest.api.auth")

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=AuthTokenResponse)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user via Supabase Auth."""
    try:
        supabase = get_supabase_client()
        result = supabase.auth.sign_up(
            {
                "email": request.email,
                "password": request.password,
                "options": {
                    "data": {"name": request.name or request.email},
                },
            }
        )

        if not result.session:
            raise BadRequestError(
                "Signup successful but no session returned. "
                "Check if email confirmation is required."
            )

        return AuthTokenResponse(
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
            expires_in=result.session.expires_in,
        )
    except BadRequestError:
        raise
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise BadRequestError(f"Signup failed: {str(e)}") from e


@router.post("/signin", response_model=AuthTokenResponse)
async def signin(
    request: SigninRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Sign in with email and password via Supabase Auth."""
    try:
        supabase = get_supabase_client()
        result = supabase.auth.sign_in_with_password(
            {
                "email": request.email,
                "password": request.password,
            }
        )

        if not result.session:
            raise UnauthorizedError("Invalid email or password")

        return AuthTokenResponse(
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
            expires_in=result.session.expires_in,
        )
    except UnauthorizedError:
        raise
    except Exception as e:
        logger.error(f"Signin failed: {e}")
        raise UnauthorizedError("Invalid email or password") from e


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh an expired access token."""
    try:
        supabase = get_supabase_client()
        result = supabase.auth.refresh_session(request.refresh_token)

        if not result.session:
            raise UnauthorizedError("Invalid refresh token")

        return AuthTokenResponse(
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
            expires_in=result.session.expires_in,
        )
    except UnauthorizedError:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise UnauthorizedError("Invalid refresh token") from e


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user profile."""
    return UserResponse.model_validate(current_user)
