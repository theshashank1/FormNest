"""
FormNest — Dynamic Form Table Service

The core innovation: auto-create and manage PostgreSQL tables per form.
Uses SQLAlchemy text() for DDL — each form gets its own strongly-typed table.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.base import FieldType

logger = logging.getLogger("formnest.services.form_table")

# Mapping from form field types to PostgreSQL column types
FIELD_TYPE_TO_PG: dict[str, str] = {
    FieldType.TEXT.value: "TEXT",
    FieldType.EMAIL.value: "TEXT",
    FieldType.PHONE.value: "TEXT",
    FieldType.NUMBER.value: "NUMERIC",
    FieldType.TEXTAREA.value: "TEXT",
    FieldType.SELECT.value: "TEXT",
    FieldType.MULTISELECT.value: "TEXT[]",
    FieldType.CHECKBOX.value: "BOOLEAN",
    FieldType.RADIO.value: "TEXT",
    FieldType.DATE.value: "DATE",
    FieldType.URL.value: "TEXT",
    FieldType.HIDDEN.value: "TEXT",
    FieldType.FILE.value: "TEXT",  # Stores file URL
    FieldType.RATING.value: "SMALLINT",
}


def _sanitize_identifier(name: str) -> str:
    """
    Sanitize a string for use as a PostgreSQL identifier.
    Only allows alphanumeric and underscores.
    """
    import re
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())
    # Ensure it doesn't start with a number
    if clean and clean[0].isdigit():
        clean = f"f_{clean}"
    return clean[:63]  # PostgreSQL identifier limit


def generate_table_name(project_id: uuid.UUID, form_id: uuid.UUID) -> str:
    """Generate a deterministic table name for a form."""
    proj_short = project_id.hex[:8]
    form_short = form_id.hex[:8]
    return f"fn_proj_{proj_short}_form_{form_short}"


class FormTableService:
    """Manages dynamic PostgreSQL tables for form submissions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_table(
        self,
        table_name: str,
        schema_fields: list[dict[str, Any]],
    ) -> None:
        """
        Create a dynamic form table based on the form schema.

        Args:
            table_name: Target table name (e.g., fn_proj_a1b2c3d4_form_e5f6g7h8)
            schema_fields: List of field definitions from form.schema
        """
        # Build column definitions
        columns = [
            "id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
            "submission_id UUID NOT NULL",
            "schema_version SMALLINT NOT NULL",
        ]

        for field in schema_fields:
            key = _sanitize_identifier(field["key"])
            field_type = field.get("type", "text")
            pg_type = FIELD_TYPE_TO_PG.get(field_type, "TEXT")
            columns.append(f"{key} {pg_type}")

        # System columns
        columns.extend([
            "submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            "ip_hash VARCHAR(64) NOT NULL",
            "a_b_variant VARCHAR(1)",
        ])

        columns_sql = ",\n    ".join(columns)
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {columns_sql}
        )
        """

        await self.db.execute(text(ddl))

        # Create indexes
        await self.db.execute(
            text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_submitted "
                 f"ON {table_name} (submitted_at DESC)")
        )
        await self.db.execute(
            text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_submission_id "
                 f"ON {table_name} (submission_id)")
        )

        logger.info(f"Created dynamic table: {table_name} with {len(schema_fields)} fields")

    async def insert_row(
        self,
        table_name: str,
        submission_id: uuid.UUID,
        schema_version: int,
        data: dict[str, Any],
        ip_hash: str,
        a_b_variant: str | None = None,
    ) -> uuid.UUID:
        """
        Insert a submission row into the dynamic table.

        Returns the generated row ID.
        """
        row_id = uuid.uuid4()

        # Build column list and values
        columns = ["id", "submission_id", "schema_version", "ip_hash"]
        values_placeholders = [":id", ":submission_id", ":schema_version", ":ip_hash"]
        params: dict[str, Any] = {
            "id": str(row_id),
            "submission_id": str(submission_id),
            "schema_version": schema_version,
            "ip_hash": ip_hash,
        }

        if a_b_variant:
            columns.append("a_b_variant")
            values_placeholders.append(":a_b_variant")
            params["a_b_variant"] = a_b_variant

        for key, value in data.items():
            safe_key = _sanitize_identifier(key)
            columns.append(safe_key)
            param_name = f"data_{safe_key}"
            values_placeholders.append(f":{param_name}")
            params[param_name] = value

        columns_sql = ", ".join(columns)
        values_sql = ", ".join(values_placeholders)

        insert_sql = f"INSERT INTO {table_name} ({columns_sql}) VALUES ({values_sql})"
        await self.db.execute(text(insert_sql), params)

        return row_id

    async def alter_table_add_column(
        self,
        table_name: str,
        field_key: str,
        field_type: str,
    ) -> None:
        """Add a new column to an existing dynamic table."""
        safe_key = _sanitize_identifier(field_key)
        pg_type = FIELD_TYPE_TO_PG.get(field_type, "TEXT")

        ddl = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {safe_key} {pg_type}"
        await self.db.execute(text(ddl))
        logger.info(f"Added column {safe_key} ({pg_type}) to {table_name}")

    async def get_row(
        self,
        table_name: str,
        row_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Fetch a single row from the dynamic table."""
        result = await self.db.execute(
            text(f"SELECT * FROM {table_name} WHERE id = :id"),
            {"id": str(row_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None
