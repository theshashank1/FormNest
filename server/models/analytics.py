"""
FormNest — Analytics Model
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from server.models.access import Project


class AnalyticsSnapshot(TimestampMixin, Base):
    """Pre-aggregated daily/hourly stats per form."""

    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    form_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("forms.id", ondelete="CASCADE"), nullable=True
    )
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    period_start: Mapped[str] = mapped_column(DateTime(timezone=False), nullable=False)
    total_submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spam_submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ghost_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    converted_ghost_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    device_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    utm_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="analytics_snapshots")

    __table_args__ = (
        Index("idx_analytics_project_period", "project_id", "period", "period_start"),
    )
