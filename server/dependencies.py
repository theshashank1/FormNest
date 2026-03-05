"""
FormNest — FastAPI Dependencies

Auth, DB session, project membership, RBAC guards.
Pattern mirrors TREEEX-WBSP dependencies.py.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.db import get_db_session
from server.core.supabase import get_supabase_client
from server.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from server.models.access import Project, ProjectMember, User
from server.models.base import MemberRole

logger = logging.getLogger("formnest.deps")


# =============================================================================
# Authentication
# =============================================================================


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Verify the Supabase JWT and return the current User.

    Same Supabase project as WBSP — shared UUIDs.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1]

    try:
        supabase = get_supabase_client()
        auth_response = supabase.auth.get_user(token)

        if not auth_response or not auth_response.user:
            raise UnauthorizedError("Invalid or expired token")

        supabase_user = auth_response.user

    except Exception as e:
        logger.warning(f"Auth verification failed: {e}")
        raise UnauthorizedError("Invalid or expired token") from e

    # Fetch or create local user record
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(supabase_user.id))
    )
    user = result.scalar_one_or_none()

    if not user:
        # First-time login — sync from Supabase
        user = User(
            id=uuid.UUID(supabase_user.id),
            email=supabase_user.email or "",
            name=supabase_user.user_metadata.get("name", supabase_user.email),
            avatar_url=supabase_user.user_metadata.get("avatar_url"),
            email_verified=supabase_user.email_confirmed_at is not None,
        )
        db.add(user)
        await db.flush()
        logger.info(f"Created new user from Supabase: {user.email}")

    elif user.is_deleted:
        raise UnauthorizedError("Account has been deactivated")

    # Store user in request state for easy access
    request.state.user = user
    return user


# =============================================================================
# Project Access
# =============================================================================


async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Fetch a project and verify the current user has access.
    """
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.deleted_at.is_(None),
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise NotFoundError("Project not found")

    # Check membership
    member_result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.status == "active",
        )
    )
    membership = member_result.scalar_one_or_none()

    if not membership and project.created_by != current_user.id:
        raise ForbiddenError("You do not have access to this project")

    return project


async def get_project_membership(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectMember:
    """
    Get the current user's membership for a project.
    """
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.status == "active",
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise ForbiddenError("You are not a member of this project")

    return membership


# =============================================================================
# Role Guards
# =============================================================================

# Role hierarchy: OWNER > ADMIN > MEMBER > VIEWER
_ROLE_HIERARCHY = {
    MemberRole.VIEWER.value: 0,
    MemberRole.MEMBER.value: 1,
    MemberRole.ADMIN.value: 2,
    MemberRole.OWNER.value: 3,
}


def require_role(min_role: MemberRole):
    """
    Dependency factory that enforces a minimum role.

    Usage:
        @router.post("/settings")
        async def update_settings(
            membership: ProjectMember = Depends(require_role(MemberRole.ADMIN)),
        ):
            ...
    """

    async def _check_role(
        membership: ProjectMember = Depends(get_project_membership),
    ) -> ProjectMember:
        user_level = _ROLE_HIERARCHY.get(membership.role, 0)
        required_level = _ROLE_HIERARCHY.get(min_role.value, 0)

        if user_level < required_level:
            raise ForbiddenError(
                f"This action requires {min_role.value} role or higher"
            )

        return membership

    return _check_role
