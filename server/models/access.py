"""
FormNest — Access Management Models

User, Project, ProjectMember, UserNotificationSettings.
User model is identical to WBSP's User for merger compatibility.
Project mirrors WBSP's Workspace with FormNest-specific columns.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import (
    Base,
    MemberRole,
    MemberStatus,
    PlanStatus,
    ProjectPlan,
    SoftDeleteMixin,
    TimestampMixin,
    generate_api_key,
    generate_slug,
)

if TYPE_CHECKING:
    from server.models.analytics import AnalyticsSnapshot
    from server.models.billing import BillingSubscription
    from server.models.blog import BlogPost
    from server.models.forms import Form
    from server.models.integrations import ProjectIntegration
    from server.models.media import MediaFile
    from server.models.tags import Tag
    from server.models.webhooks import Webhook


class User(TimestampMixin, SoftDeleteMixin, Base):
    """
    Global user registry — synced from Supabase Auth.

    Schema is IDENTICAL to WBSP's User model for merger compatibility.
    Same Supabase project → same UUIDs → zero migration needed.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    owned_projects: Mapped[list[Project]] = relationship(
        "Project", back_populates="owner", foreign_keys="Project.created_by"
    )
    memberships: Mapped[list[ProjectMember]] = relationship(
        "ProjectMember",
        back_populates="user",
        foreign_keys="ProjectMember.user_id",
        cascade="all, delete-orphan",
    )
    notification_settings: Mapped[UserNotificationSettings | None] = relationship(
        "UserNotificationSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_active", "is_active"),
        Index("idx_user_deleted", "deleted_at"),
    )


class Project(TimestampMixin, SoftDeleteMixin, Base):
    """
    Top-level tenant isolation unit.

    Equivalent to WBSP's Workspace. Named 'projects' for developer friendliness.
    In the future merger, projects.wbsp_workspace_id links to the unified workspace.
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    api_key: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False, default=generate_api_key
    )
    webhook_secret: Mapped[uuid.UUID] = mapped_column(
        Uuid, unique=True, nullable=False, default=uuid.uuid4
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Plan & usage
    plan: Mapped[str] = mapped_column(
        String(20), default=ProjectPlan.FREE.value, nullable=False
    )
    plan_status: Mapped[str] = mapped_column(
        String(20), default=PlanStatus.ACTIVE.value, nullable=False
    )
    submission_limit_monthly: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False  # Free plan: 100/month
    )
    submission_used_this_month: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    form_limit: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False  # Free plan: 3 forms
    )
    blog_posts_limit: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False  # Free plan: 5 posts
    )

    # Settings
    settings: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_domain_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- MERGER STUBS (nullable, populated when WBSP bridge activates) ---
    wbsp_workspace_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    wbsp_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    owner: Mapped[User] = relationship(
        "User", back_populates="owned_projects", foreign_keys=[created_by]
    )
    members: Mapped[list[ProjectMember]] = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    forms: Mapped[list[Form]] = relationship(
        "Form", back_populates="project", cascade="all, delete-orphan"
    )
    tags: Mapped[list[Tag]] = relationship(
        "Tag", back_populates="project", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list[Webhook]] = relationship(
        "Webhook", back_populates="project", cascade="all, delete-orphan"
    )
    integrations: Mapped[list[ProjectIntegration]] = relationship(
        "ProjectIntegration", back_populates="project", cascade="all, delete-orphan"
    )
    blog_posts: Mapped[list[BlogPost]] = relationship(
        "BlogPost", back_populates="project", cascade="all, delete-orphan"
    )
    analytics_snapshots: Mapped[list[AnalyticsSnapshot]] = relationship(
        "AnalyticsSnapshot", back_populates="project", cascade="all, delete-orphan"
    )
    media_files: Mapped[list[MediaFile]] = relationship(
        "MediaFile", back_populates="project", cascade="all, delete-orphan"
    )
    billing_subscription: Mapped[BillingSubscription | None] = relationship(
        "BillingSubscription", back_populates="project", uselist=False
    )

    __table_args__ = (
        Index("idx_project_slug", "slug"),
        Index("idx_project_api_key", "api_key"),
        Index("idx_project_created_by", "created_by"),
        Index("idx_project_plan", "plan", "plan_status"),
        Index("idx_project_active", "deleted_at"),
    )

    def __init__(self, **kwargs):
        if "slug" not in kwargs and "name" in kwargs:
            kwargs["slug"] = generate_slug(kwargs["name"])
        super().__init__(**kwargs)


class ProjectMember(TimestampMixin, Base):
    """
    Links users to projects with roles.

    Identical RBAC model to WBSP's WorkspaceMember.
    Role names are compatible for merger.
    """

    __tablename__ = "project_members"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), default=MemberRole.MEMBER.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=MemberStatus.ACTIVE.value, nullable=False
    )

    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invited_at: Mapped[datetime | None] = mapped_column(nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(nullable=True)
    permissions: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="members")
    user: Mapped[User] = relationship(
        "User", back_populates="memberships", foreign_keys=[user_id]
    )
    inviter: Mapped[User | None] = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        Index("idx_project_member_unique", "project_id", "user_id", unique=True),
        Index("idx_project_member_project", "project_id"),
        Index("idx_project_member_user", "user_id"),
        Index("idx_project_member_role", "role"),
    )


class UserNotificationSettings(TimestampMixin, Base):
    """Per-user notification preferences."""

    __tablename__ = "user_notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    email_new_submission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_usage_warning: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_weekly_digest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_marketing: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="notification_settings")

    __table_args__ = (
        Index("idx_notif_user", "user_id"),
    )
