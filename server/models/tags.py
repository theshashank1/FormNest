"""
FormNest — Tag Model

Identical schema to WBSP tags for merger compatibility.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from server.models.access import Project
    from server.models.submissions import SubmissionTagLink


class Tag(TimestampMixin, Base):
    """Reusable labels for lead segmentation. Schema identical to WBSP tags."""

    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#22C55E")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="tags")
    submission_links: Mapped[list[SubmissionTagLink]] = relationship(
        "SubmissionTagLink", back_populates="tag", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_tag_project_name", "project_id", "name", unique=True),
        Index("idx_tag_project", "project_id"),
    )
