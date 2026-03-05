"""
FormNest — Form Schemas
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- Field Definition ---

class FormFieldDefinition(BaseModel):
    """Single field in a form schema."""
    key: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=255)
    type: str  # FieldType enum value
    required: bool = False
    placeholder: str | None = None
    validation: dict[str, Any] | None = None
    options: list[str] | None = None  # For select/radio/multiselect
    step: int | None = None  # For multi-step forms
    conditional: dict[str, Any] | None = None  # Show/hide logic


# --- Requests ---

class CreateFormRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    schema_fields: list[FormFieldDefinition] = Field(alias="schema")
    form_type: str = "single_page"
    steps_config: dict[str, Any] | None = None
    success_message: str | None = None
    redirect_url: str | None = None
    styling: dict[str, Any] | None = None
    spam_protection: dict[str, Any] | None = None

    model_config = {"populate_by_name": True}


class UpdateFormRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    schema_fields: list[FormFieldDefinition] | None = Field(None, alias="schema")
    form_type: str | None = None
    steps_config: dict[str, Any] | None = None
    success_message: str | None = None
    redirect_url: str | None = None
    is_active: bool | None = None
    styling: dict[str, Any] | None = None
    spam_protection: dict[str, Any] | None = None
    allowed_origins: list[str] | None = None

    model_config = {"populate_by_name": True}


# --- Responses ---

class FormResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    form_key: str
    schema_fields: list[dict[str, Any]] = Field(alias="schema")
    schema_version: int
    form_type: str
    steps_config: dict[str, Any] | None = None
    table_name: str
    table_created: bool
    is_active: bool
    submission_count: int
    success_message: str | None = None
    redirect_url: str | None = None
    spam_protection: dict[str, Any]
    styling: dict[str, Any] | None = None
    partial_save_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class FormListResponse(BaseModel):
    forms: list[FormResponse]
    total: int
