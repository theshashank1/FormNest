"""
FormNest — Form Models

Form definitions and schema version history.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, SmallInteger, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import (
    Base,
    FormType,
    SoftDeleteMixin,
    TimestampMixin,
    generate_form_key,
)

if TYPE_CHECKING:
    from server.models.access import Project, User
    from server.models.submissions import FormSubmissionIndex, GhostLead
    from server.models.webhooks import Webhook


class Form(TimestampMixin, SoftDeleteMixin, Base):
    """
    Form definition — field schema, embed config, spam protection.

    Each active form auto-creates a PostgreSQL table: fn_proj_{id}_form_{id}
    """

    __tablename__ = "forms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    form_key: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False, default=generate_form_key
    )

    # Schema definition (JSONB array of field definitions)
    schema: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    schema_version: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)

    # Form type & config
    form_type: Mapped[str] = mapped_column(
        String(20), default=FormType.SINGLE_PAGE.value, nullable=False
    )
    steps_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Dynamic table tracking
    table_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    table_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Status & counters
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    submission_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # UX customisation
    success_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_origins: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Spam protection config
    spam_protection: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "honeypot_field": "_gotcha",
            "rate_limit": 5,
            "captcha_enabled": False,
            "min_time_seconds": 2,
        },
    )

    # Styling
    styling: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # A/B testing (Phase 2)
    a_b_test_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    a_b_variant_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Ghost leads
    partial_save_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Audit
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="forms")
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])
    schema_versions: Mapped[list[FormSchemaVersion]] = relationship(
        "FormSchemaVersion", back_populates="form", cascade="all, delete-orphan"
    )
    submissions: Mapped[list[FormSubmissionIndex]] = relationship(
        "FormSubmissionIndex", back_populates="form", cascade="all, delete-orphan"
    )
    ghost_leads: Mapped[list[GhostLead]] = relationship(
        "GhostLead", back_populates="form", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list[Webhook]] = relationship(
        "Webhook", back_populates="form"
    )

    __table_args__ = (
        Index("idx_form_key", "form_key"),
        Index("idx_form_table_name", "table_name"),
        Index("idx_form_project", "project_id"),
        Index("idx_form_active", "project_id", "is_active", "deleted_at"),
    )


class FormSchemaVersion(TimestampMixin, Base):
    """Immutable history of every schema change."""

    __tablename__ = "form_schema_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("forms.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    schema_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Relationships
    form: Mapped[Form] = relationship("Form", back_populates="schema_versions")
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("idx_schema_version_unique", "form_id", "version", unique=True),
        Index("idx_schema_version_form", "form_id"),
    )
