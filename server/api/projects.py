"""
FormNest — Project API Routes
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.db import get_db_session
from server.dependencies import get_current_user, get_project
from server.models.access import Project, ProjectMember, User
from server.models.base import MemberRole, MemberStatus, generate_api_key
from server.schemas.projects import (
    ApiKeyResponse,
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    UpdateProjectRequest,
)

logger = logging.getLogger("formnest.api.projects")

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    """Create a new project and assign the creator as OWNER."""
    project = Project(
        name=request.name,
        created_by=current_user.id,
        notification_email=request.notification_email or current_user.email,
    )
    db.add(project)
    await db.flush()

    # Auto-create OWNER membership
    membership = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=MemberRole.OWNER.value,
        status=MemberStatus.ACTIVE.value,
    )
    db.add(membership)
    await db.flush()

    logger.info(f"Project created: {project.name} ({project.slug})")
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProjectListResponse:
    """List all projects the current user has access to."""
    result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.user_id == current_user.id,
            ProjectMember.status == MemberStatus.ACTIVE.value,
            Project.deleted_at.is_(None),
        )
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=len(projects),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_detail(
    project: Project = Depends(get_project),
) -> ProjectResponse:
    """Get project details."""
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    request: UpdateProjectRequest,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    """Update project settings."""
    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "settings" and value:
            # Merge settings instead of replacing
            current_settings = project.settings or {}
            current_settings.update(value)
            project.settings = current_settings
        else:
            setattr(project, field, value)

    await db.flush()
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}/api-key", response_model=ApiKeyResponse)
async def get_api_key(
    project: Project = Depends(get_project),
    current_user: User = Depends(get_current_user),
) -> ApiKeyResponse:
    """
    Retrieve the current project API key.

    The API key grants **project-level** access and can be used as an
    alternative to JWT tokens for server-to-server or CLI integrations.
    Pass it in the ``X-API-Key`` request header.

    Only project **owners** and **admins** should access this endpoint.
    Store the key securely — treat it like a password.
    """
    return ApiKeyResponse(api_key=project.api_key)


@router.post("/{project_id}/api-key/rotate", response_model=ApiKeyResponse)
async def rotate_api_key(
    project: Project = Depends(get_project),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiKeyResponse:
    """
    Rotate the project API key.

    Generates a new ``fn_`` prefixed API key and **immediately invalidates** the
    old one. Any integrations using the old key will start receiving
    ``401 Unauthorized`` errors — update them before rotating.

    This action is logged for security auditing purposes.
    """
    old_key = project.api_key
    new_key = generate_api_key()
    project.api_key = new_key
    await db.flush()

    logger.info(
        f"API key rotated for project '{project.name}' ({project.id}) "
        f"by user {current_user.id}. Old prefix: {old_key[:8]}…"
    )

    return ApiKeyResponse(api_key=new_key)
