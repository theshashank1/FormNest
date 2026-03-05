"""
FormNest — Media File Model
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from server.models.access import Project, User


class MediaFile(TimestampMixin, SoftDeleteMixin, Base):
    """Media file metadata. Files stored in Cloudflare R2."""

    __tablename__ = "media_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="media_files")
    uploader: Mapped[User] = relationship("User", foreign_keys=[uploaded_by])

    __table_args__ = (
        Index("idx_media_project", "project_id"),
        Index("idx_media_type_purpose", "type", "purpose"),
    )
