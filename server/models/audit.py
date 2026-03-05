"""
FormNest — Audit & Log Models
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, SmallInteger, String, Text, Uuid
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from server.models.base import Base


class ApiAccessLog(Base):
    """Lightweight request audit log. Retention: 30 days."""

    __tablename__ = "api_access_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: __import__("server.models.base", fromlist=["utc_now"]).utc_now()
    )

    __table_args__ = (
        Index("idx_api_log_project", "project_id", "created_at"),
        Index("idx_api_log_time", "created_at"),
    )


class EmailLog(Base):
    """Log of all outbound email attempts. Retention: 60 days."""

    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    email_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    resend_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: __import__("server.models.base", fromlist=["utc_now"]).utc_now()
    )

    __table_args__ = (
        Index("idx_email_log_project", "project_id", "created_at"),
        Index("idx_email_log_status", "status", "created_at"),
    )
