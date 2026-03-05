"""
FormNest — Submission Schemas
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

# --- Public Submit Request ---

class SubmitFormRequest(BaseModel):
    """
    Public form submission payload.
    Fields are dynamic — validated against the form schema at runtime.
    """
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None  # UTM, referrer, device


class SubmitFormResponse(BaseModel):
    """Response for successful submission."""
    submission_id: UUID
    message: str = "Submission received"


# --- Dashboard Responses ---

class SubmissionResponse(BaseModel):
    id: UUID
    form_id: UUID
    form_key: str
    is_spam: bool
    spam_score: int
    name: str | None = None
    email: str | None = None  # Masked in list view
    phone: str | None = None  # Masked in list view
    data_snapshot: dict[str, Any]
    source_url: str | None = None
    referrer: str | None = None
    device: str | None = None
    utm_data: dict[str, Any] | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class SubmissionDetailResponse(SubmissionResponse):
    """Full submission detail — includes data from the dynamic table."""
    full_data: dict[str, Any] = {}  # Populated from dynamic table


class SubmissionListResponse(BaseModel):
    submissions: list[SubmissionResponse]
    total: int
    page: int
    page_size: int
