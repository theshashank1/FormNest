"""
FormNest — Submission API Routes

Public submission endpoint + authenticated dashboard endpoints.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.db import get_db_session
from server.dependencies import get_current_user, get_project
from server.exceptions import NotFoundError
from server.models.access import Project, User
from server.models.submissions import FormSubmissionIndex
from server.schemas.submissions import (
    SubmissionDetailResponse,
    SubmissionListResponse,
    SubmissionResponse,
    SubmitFormRequest,
    SubmitFormResponse,
)
from server.services.submission_service import SubmissionService

logger = logging.getLogger("formnest.api.submissions")

router = APIRouter(tags=["Submissions"])


# =============================================================================
# PUBLIC endpoint — no auth required
# =============================================================================


@router.post("/submit/{form_key}", response_model=SubmitFormResponse, status_code=202)
async def submit_form(
    form_key: str,
    request: SubmitFormRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Public form submission endpoint.

    Accepts submissions from any website embedding the FormNest widget.
    No authentication required — form_key is the only identifier.

    Rate limited: 5 submissions/minute per IP per form_key.
    """
    # Get client IP
    client_ip = http_request.client.host if http_request.client else "0.0.0.0"
    forwarded = http_request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    # Process submission
    service = SubmissionService(db)
    submission_id = await service.process_submission(
        form_key=form_key,
        data=request.data,
        metadata=request.metadata,
        client_ip=client_ip,
    )

    return SubmitFormResponse(
        submission_id=submission_id,
        message="Submission received",
    )


# =============================================================================
# Authenticated dashboard endpoints
# =============================================================================


@router.get(
    "/api/v1/projects/{project_id}/forms/{form_id}/submissions",
    response_model=SubmissionListResponse,
)
async def list_submissions(
    project_id: uuid.UUID,
    form_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_spam: bool = Query(False),
    project: Project = Depends(get_project),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List form submissions with pagination."""
    # Build query
    query = (
        select(FormSubmissionIndex)
        .where(
            FormSubmissionIndex.project_id == project.id,
            FormSubmissionIndex.form_id == form_id,
            FormSubmissionIndex.is_spam == is_spam,
        )
        .order_by(FormSubmissionIndex.submitted_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    submissions = result.scalars().all()

    # Get total count
    count_query = (
        select(func.count())
        .select_from(FormSubmissionIndex)
        .where(
            FormSubmissionIndex.project_id == project.id,
            FormSubmissionIndex.form_id == form_id,
            FormSubmissionIndex.is_spam == is_spam,
        )
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return SubmissionListResponse(
        submissions=[
            SubmissionResponse.model_validate(s) for s in submissions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/api/v1/projects/{project_id}/forms/{form_id}/submissions/{submission_id}",
    response_model=SubmissionDetailResponse,
)
async def get_submission_detail(
    project_id: uuid.UUID,
    form_id: uuid.UUID,
    submission_id: uuid.UUID,
    project: Project = Depends(get_project),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get full submission detail including data from dynamic table."""
    result = await db.execute(
        select(FormSubmissionIndex).where(
            FormSubmissionIndex.id == submission_id,
            FormSubmissionIndex.project_id == project.id,
            FormSubmissionIndex.form_id == form_id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise NotFoundError("Submission not found")

    # Mark as reviewed if first time
    if not submission.reviewed_at:
        from server.models.base import utc_now
        submission.reviewed_at = utc_now()
        await db.flush()

    # Fetch full data from dynamic table
    from server.models.forms import Form
    from server.services.form_table_service import FormTableService

    form_result = await db.execute(select(Form).where(Form.id == form_id))
    form = form_result.scalar_one_or_none()

    full_data = {}
    if form and form.table_created:
        table_service = FormTableService(db)
        row = await table_service.get_row(
            form.table_name,
            submission.dynamic_table_row_id,
        )
        if row:
            # Filter out system columns
            full_data = {
                k: v for k, v in row.items()
                if k not in ("id", "submission_id", "schema_version", "submitted_at", "ip_hash", "a_b_variant")
            }

    response = SubmissionDetailResponse.model_validate(submission)
    response.full_data = full_data
    return response
