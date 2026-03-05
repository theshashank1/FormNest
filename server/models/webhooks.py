"""
FormNest — Webhook Models

Outbound webhook configurations and delivery logs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from server.models.access import Project, User
    from server.models.forms import Form


class Webhook(TimestampMixin, Base):
    """Outbound webhook configurations per project."""

    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    events: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    form_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("forms.id", ondelete="SET NULL"), nullable=True
    )
    headers: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    auto_disabled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="webhooks")
    form: Mapped[Form | None] = relationship("Form", back_populates="webhooks")
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])
    delivery_logs: Mapped[list[WebhookDeliveryLog]] = relationship(
        "WebhookDeliveryLog", back_populates="webhook", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_webhook_project", "project_id"),
        Index("idx_webhook_form", "form_id"),
        Index("idx_webhook_active", "project_id", "is_active"),
    )


class WebhookDeliveryLog(Base):
    """Per-attempt delivery log for outbound webhooks."""

    __tablename__ = "webhook_delivery_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("form_submission_index.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    http_status_code: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: __import__("server.models.base", fromlist=["utc_now"]).utc_now()
    )

    # Relationships
    webhook: Mapped[Webhook] = relationship("Webhook", back_populates="delivery_logs")

    __table_args__ = (
        Index("idx_wdl_webhook", "webhook_id", "attempted_at"),
        Index("idx_wdl_submission", "submission_id"),
        Index("idx_wdl_status", "status", "attempted_at"),
    )
