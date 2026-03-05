"""
FormNest — ORM Base Classes, Mixins & Enums

Mirrors TREEEX-WBSP models/base.py for merger compatibility.
Shared patterns: Base, TimestampMixin, SoftDeleteMixin, MemberRole, MemberStatus.
"""

from __future__ import annotations

import enum
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Current UTC time as naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug with unique suffix."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    suffix = uuid.uuid4().hex[:6]
    return f"{slug}-{suffix}" if slug else f"project-{suffix}"


def generate_form_key() -> str:
    """Generate a unique form key with fm_ prefix."""
    return f"fm_{uuid.uuid4().hex[:12]}"


def generate_api_key() -> str:
    """Generate a unique project API key with fn_ prefix."""
    return f"fn_{uuid.uuid4().hex[:32]}"


# =============================================================================
# ENUMS — Shared with WBSP where noted
# =============================================================================


# --- Access / Membership (shared with WBSP) ---

class MemberRole(enum.StrEnum):
    """Workspace/project member roles. Compatible with WBSP MemberRole."""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"  # FormNest-specific: read-only access


class MemberStatus(enum.StrEnum):
    """Member invitation status. Compatible with WBSP MemberStatus."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


# --- Project ---

class ProjectPlan(enum.StrEnum):
    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    AGENCY = "agency"
    ENTERPRISE = "enterprise"


class PlanStatus(enum.StrEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    TRIALING = "trialing"


# --- Forms ---

class FormType(enum.StrEnum):
    SINGLE_PAGE = "single_page"
    MULTI_STEP = "multi_step"
    SURVEY = "survey"


class FieldType(enum.StrEnum):
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    NUMBER = "number"
    TEXTAREA = "textarea"
    SELECT = "select"
    MULTISELECT = "multiselect"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DATE = "date"
    URL = "url"
    HIDDEN = "hidden"
    FILE = "file"
    RATING = "rating"


# --- Blog ---

class BlogPostStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PSeoDatasetStatus(enum.StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    FAILED = "failed"
    SKIPPED = "skipped"


# --- Integrations ---

class IntegrationType(enum.StrEnum):
    NOTION = "notion"
    GOOGLE_SHEETS = "google_sheets"
    SLACK = "slack"
    AIRTABLE = "airtable"
    ZAPIER = "zapier"


# --- Webhooks ---

class WebhookEvent(enum.StrEnum):
    FORM_SUBMISSION = "form.submission"
    FORM_SPAM = "form.spam"
    FORM_GHOST_LEAD = "form.ghost_lead"


# --- Email ---

class EmailType(enum.StrEnum):
    NEW_SUBMISSION = "new_submission"
    USAGE_WARNING_80 = "usage_warning_80"
    USAGE_LIMIT_REACHED = "usage_limit_reached"
    WELCOME = "welcome"
    SUBSCRIPTION_ACTIVATED = "subscription_activated"
    WEEKLY_DIGEST = "weekly_digest"


class EmailStatus(enum.StrEnum):
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


# --- Media ---

class MediaType(enum.StrEnum):
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"


class MediaPurpose(enum.StrEnum):
    BLOG_IMAGE = "blog_image"
    FORM_UPLOAD = "form_upload"
    OG_IMAGE = "og_image"
    AVATAR = "avatar"


# --- Billing ---

class BillingProvider(enum.StrEnum):
    RAZORPAY = "razorpay"
    STRIPE = "stripe"


class BillingCycle(enum.StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


# --- Analytics ---

class AnalyticsPeriod(enum.StrEnum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# --- Delivery ---

class DeliveryStatus(enum.StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


# =============================================================================
# BASE & MIXINS — Identical to WBSP
# =============================================================================


class Base(DeclarativeBase):
    """Base class for all models."""

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            if isinstance(val, (datetime, uuid.UUID)):
                val = str(val)
            if isinstance(val, enum.Enum):
                val = val.value
            result[col.name] = val
        return result


class TimestampMixin:
    """Standard created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False,
    )


class SoftDeleteMixin:
    """Soft delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = utc_now()

    def restore(self) -> None:
        self.deleted_at = None
