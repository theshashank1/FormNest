"""
FormNest — Billing Models
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from server.models.access import Project, User


class BillingSubscription(TimestampMixin, Base):
    """Razorpay and Stripe subscription tracking."""

    __tablename__ = "billing_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_subscription_id: Mapped[str] = mapped_column(Text, nullable=False)
    provider_customer_id: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(10), nullable=False)
    amount_subunit: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(nullable=True)
    current_period_start: Mapped[datetime] = mapped_column(nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="billing_subscription")
    subscriber: Mapped[User] = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_billing_project", "project_id"),
        Index("idx_billing_provider_sub", "provider", "provider_subscription_id", unique=True),
        Index("idx_billing_status", "status"),
    )


class BillingEvent(Base):
    """Webhook event log from Razorpay / Stripe. Idempotency guard."""

    __tablename__ = "billing_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    event_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: __import__("server.models.base", fromlist=["utc_now"]).utc_now()
    )

    __table_args__ = (
        Index("idx_billing_event_id", "provider", "event_id", unique=True),
        Index("idx_billing_event_project", "project_id"),
        Index("idx_billing_event_unprocessed", "processed", "created_at"),
    )
