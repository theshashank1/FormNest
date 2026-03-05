"""
FormNest — Submission Models

FormSubmissionIndex (central lead index), GhostLead, SubmissionTagLink.
Includes WBSP merger stubs for contact bridge.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, Text, Uuid
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base

if TYPE_CHECKING:
    from server.models.access import Project, User
    from server.models.forms import Form, FormSchemaVersion
    from server.models.tags import Tag


class FormSubmissionIndex(Base):
    """
    Central index of all submissions across all dynamic form tables.

    Primary table for dashboard queries, analytics, and WBSP bridge.
    Full data lives in dynamic tables; this is the lightweight index.
    """

    __tablename__ = "form_submission_index"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    form_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("forms.id", ondelete="CASCADE"), nullable=False
    )
    form_key: Mapped[str] = mapped_column(String(40), nullable=False)  # Denormalised
    schema_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("form_schema_versions.id", ondelete="RESTRICT"), nullable=False
    )
    dynamic_table_row_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

    # Spam
    is_spam: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    spam_score: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    # Contact info (PII — should be encrypted at application layer)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Snapshot of first 5 fields
    data_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Source metadata
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    referrer: Mapped[str | None] = mapped_column(Text, nullable=True)
    device: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    utm_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # A/B variant
    a_b_variant: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: __import__("server.models.base", fromlist=["utc_now"]).utc_now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # --- MERGER STUBS ---
    wbsp_contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    wbsp_synced_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    project: Mapped[Project] = relationship("Project")
    form: Mapped[Form] = relationship("Form", back_populates="submissions")
    schema_version: Mapped[FormSchemaVersion] = relationship("FormSchemaVersion")
    tag_links: Mapped[list[SubmissionTagLink]] = relationship(
        "SubmissionTagLink", back_populates="submission", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_sub_idx_project_time", "project_id", "submitted_at"),
        Index("idx_sub_idx_form_time", "form_id", "submitted_at"),
        Index("idx_sub_idx_email", "email"),
        Index("idx_sub_idx_phone", "phone"),
        Index("idx_sub_idx_spam", "project_id", "is_spam"),
    )


class GhostLead(Base):
    """
    Partial form fills that were never submitted.
    Captured by the partial_save widget feature.
    """

    __tablename__ = "ghost_leads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("forms.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    partial_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Contact info if captured (PII)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Multi-step tracking
    last_step_reached: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Source
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    device: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: __import__("server.models.base", fromlist=["utc_now"]).utc_now()
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    converted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    converted_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("form_submission_index.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    form: Mapped[Form] = relationship("Form", back_populates="ghost_leads")
    project: Mapped[Project] = relationship("Project")

    __table_args__ = (
        Index("idx_ghost_form", "form_id", "created_at"),
        Index("idx_ghost_email", "email"),
        Index("idx_ghost_expires", "expires_at"),
    )


class SubmissionTagLink(Base):
    """M2M junction: form_submission_index ↔ tags."""

    __tablename__ = "submission_tag_links"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("form_submission_index.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tagged_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: __import__("server.models.base", fromlist=["utc_now"]).utc_now()
    )

    # Relationships
    submission: Mapped[FormSubmissionIndex] = relationship(
        "FormSubmissionIndex", back_populates="tag_links"
    )
    tag: Mapped[Tag] = relationship("Tag", back_populates="submission_links")
    tagger: Mapped[User] = relationship("User")

    __table_args__ = (
        Index("idx_sub_tag_submission", "submission_id"),
        Index("idx_sub_tag_tag", "tag_id"),
    )
