"""
FormNest — Blog & Programmatic SEO Models
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, SmallInteger, String, Text, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, BlogPostStatus, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from server.models.access import Project, User


class BlogPost(TimestampMixin, SoftDeleteMixin, Base):
    """Blog post content + SEO metadata."""

    __tablename__ = "blog_posts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=BlogPostStatus.DRAFT.value, nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # SEO
    seo_title: Mapped[str | None] = mapped_column(String(70), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(160), nullable=True)
    seo_keywords: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    og_title: Mapped[str | None] = mapped_column(String(70), nullable=True)
    og_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    og_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_markup: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Stats
    reading_time_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tags: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)

    # Programmatic SEO
    is_programmatic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pse_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("programmatic_seo_templates.id", ondelete="SET NULL"), nullable=True
    )
    pse_dataset_row_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    # Full-text search (populated by DB trigger)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="blog_posts")
    author: Mapped[User] = relationship("User", foreign_keys=[author_id])

    __table_args__ = (
        Index("idx_blog_project_slug", "project_id", "slug", unique=True),
        Index("idx_blog_project_status", "project_id", "status", "published_at"),
        Index("idx_blog_published", "published_at"),
        Index("idx_blog_programmatic", "project_id", "is_programmatic"),
    )


class ProgrammaticSeoTemplate(TimestampMixin, Base):
    """Template definitions for generating bulk SEO pages."""

    __tablename__ = "programmatic_seo_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title_template: Mapped[str] = mapped_column(String(255), nullable=False)
    content_template: Mapped[str] = mapped_column(Text, nullable=False)
    seo_description_template: Mapped[str | None] = mapped_column(String(200), nullable=True)
    slug_template: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_template: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Relationships
    project: Mapped[Project] = relationship("Project")
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("idx_pse_template_project", "project_id"),
    )


class ProgrammaticSeoDataset(Base):
    """CSV data rows used to hydrate PSeo templates."""

    __tablename__ = "programmatic_seo_datasets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programmatic_seo_templates.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    variables: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    blog_post_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("blog_posts.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: __import__("server.models.base", fromlist=["utc_now"]).utc_now()
    )

    # Relationships
    template: Mapped[ProgrammaticSeoTemplate] = relationship("ProgrammaticSeoTemplate")
    project: Mapped[Project] = relationship("Project")

    __table_args__ = (
        Index("idx_pse_dataset_template", "template_id", "status"),
        Index("idx_pse_dataset_post", "blog_post_id"),
    )
