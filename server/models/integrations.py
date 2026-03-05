"""
FormNest — Integration Model
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from server.models.access import Project, User


class ProjectIntegration(TimestampMixin, Base):
    """Third-party integration configs (Notion, Google Sheets, Slack, etc.)."""

    __tablename__ = "project_integrations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    integration_type: Mapped[str] = mapped_column(String(30), nullable=False)
    form_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("forms.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    credentials: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # Encrypted at app layer
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="integrations")
    creator: Mapped[User] = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("idx_integration_project", "project_id"),
    )
