"""
FormNest — Form API Routes
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.db import get_db_session
from server.dependencies import get_current_user, get_project
from server.exceptions import NotFoundError, PlanLimitError
from server.models.access import Project, User
from server.models.forms import Form, FormSchemaVersion
from server.schemas.forms import (
    CreateFormRequest,
    FormListResponse,
    FormResponse,
    UpdateFormRequest,
)
from server.services.form_table_service import FormTableService, generate_table_name

logger = logging.getLogger("formnest.api.forms")

router = APIRouter(prefix="/projects/{project_id}/forms", tags=["Forms"])


@router.post("", response_model=FormResponse, status_code=201)
async def create_form(
    project_id: uuid.UUID,
    request: CreateFormRequest,
    project: Project = Depends(get_project),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new form and auto-provision its database table."""
    # Check form limit
    result = await db.execute(
        select(Form).where(
            Form.project_id == project.id,
            Form.deleted_at.is_(None),
        )
    )
    existing_forms = result.scalars().all()
    if len(existing_forms) >= project.form_limit:
        raise PlanLimitError(f"Form limit ({project.form_limit}) reached for your plan")

    # Generate form ID and table name
    form_id = uuid.uuid4()
    table_name = generate_table_name(project.id, form_id)

    # Create form record
    schema_dict = [f.model_dump() for f in request.schema_fields]
    form = Form(
        id=form_id,
        project_id=project.id,
        name=request.name,
        schema=schema_dict,
        form_type=request.form_type,
        steps_config=request.steps_config,
        table_name=table_name,
        success_message=request.success_message,
        redirect_url=request.redirect_url,
        styling=request.styling,
        spam_protection=request.spam_protection or {
            "honeypot_field": "_gotcha",
            "rate_limit": 5,
            "captcha_enabled": False,
            "min_time_seconds": 2,
        },
        created_by=current_user.id,
    )
    db.add(form)
    await db.flush()

    # Create initial schema version
    schema_version = FormSchemaVersion(
        form_id=form.id,
        version=1,
        schema_snapshot=schema_dict,
        change_reason="Initial form creation",
        created_by=current_user.id,
    )
    db.add(schema_version)

    # Create the dynamic table
    table_service = FormTableService(db)
    await table_service.create_table(table_name, schema_dict)
    form.table_created = True

    await db.flush()
    logger.info(f"Form created: {form.name} (key={form.form_key}, table={table_name})")

    return FormResponse.model_validate(form)


@router.get("", response_model=FormListResponse)
async def list_forms(
    project_id: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db_session),
):
    """List all forms in a project."""
    result = await db.execute(
        select(Form).where(
            Form.project_id == project.id,
            Form.deleted_at.is_(None),
        ).order_by(Form.created_at.desc())
    )
    forms = result.scalars().all()

    return FormListResponse(
        forms=[FormResponse.model_validate(f) for f in forms],
        total=len(forms),
    )


@router.get("/{form_id}", response_model=FormResponse)
async def get_form(
    form_id: uuid.UUID,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db_session),
):
    """Get form schema and details."""
    result = await db.execute(
        select(Form).where(
            Form.id == form_id,
            Form.project_id == project.id,
            Form.deleted_at.is_(None),
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise NotFoundError("Form not found")

    return FormResponse.model_validate(form)


@router.delete("/{form_id}", status_code=204)
async def delete_form(
    form_id: uuid.UUID,
    project: Project = Depends(get_project),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Soft-delete a form.

    The form is marked as deleted and deactivated immediately so it no longer
    accepts new submissions. The underlying data table is preserved for audit
    purposes and can be recovered by support if needed within 30 days.
    """
    from server.models.base import utc_now

    result = await db.execute(
        select(Form).where(
            Form.id == form_id,
            Form.project_id == project.id,
            Form.deleted_at.is_(None),
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise NotFoundError("Form not found")

    form.deleted_at = utc_now()
    form.is_active = False
    await db.flush()
    logger.info(f"Form soft-deleted: {form.name} ({form.form_key}) by user {current_user.id}")

async def update_form(
    form_id: uuid.UUID,
    request: UpdateFormRequest,
    project: Project = Depends(get_project),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update form schema or settings."""
    result = await db.execute(
        select(Form).where(
            Form.id == form_id,
            Form.project_id == project.id,
            Form.deleted_at.is_(None),
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise NotFoundError("Form not found")

    update_data = request.model_dump(exclude_unset=True)

    # Handle schema update — creates new version + alters table
    if "schema_fields" in update_data and update_data["schema_fields"] is not None:
        new_schema = update_data.pop("schema_fields")
        new_schema_dict = [f.model_dump() if hasattr(f, 'model_dump') else f for f in new_schema]

        old_keys = {f["key"] for f in form.schema}
        new_keys = {f["key"] for f in new_schema_dict}
        added_keys = new_keys - old_keys

        # Add new columns to dynamic table
        if added_keys and form.table_created:
            table_service = FormTableService(db)
            for field_def in new_schema_dict:
                if field_def["key"] in added_keys:
                    await table_service.alter_table_add_column(
                        form.table_name,
                        field_def["key"],
                        field_def.get("type", "text"),
                    )

        # Increment version
        form.schema = new_schema_dict
        form.schema_version += 1

        # Save new version
        version = FormSchemaVersion(
            form_id=form.id,
            version=form.schema_version,
            schema_snapshot=new_schema_dict,
            change_reason="Schema updated",
            created_by=current_user.id,
        )
        db.add(version)

    # Apply other updates
    for field, value in update_data.items():
        setattr(form, field, value)

    await db.flush()
    return FormResponse.model_validate(form)
