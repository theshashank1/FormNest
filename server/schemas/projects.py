"""
FormNest — Project Schemas
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# --- Requests ---

class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    notification_email: str | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    notification_email: str | None = None
    settings: dict | None = None
    custom_domain: str | None = None


# --- Responses ---

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    api_key: str
    plan: str
    plan_status: str
    submission_limit_monthly: int
    submission_used_this_month: int
    form_limit: int
    blog_posts_limit: int
    custom_domain: str | None = None
    custom_domain_verified: bool
    notification_email: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
