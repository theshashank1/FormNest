"""
FormNest — Submission Processing Service

Handles form submission validation, spam checking, and storage.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.exceptions import FormNotActiveError, PlanLimitError
from server.models.access import Project
from server.models.forms import Form, FormSchemaVersion
from server.models.submissions import FormSubmissionIndex
from server.services.form_table_service import FormTableService

logger = logging.getLogger("formnest.services.submission")


class SubmissionService:
    """Process and store form submissions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.table_service = FormTableService(db)

    async def process_submission(
        self,
        form_key: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        client_ip: str = "0.0.0.0",
    ) -> uuid.UUID:
        """
        Full submission processing pipeline:
        1. Lookup form by form_key
        2. Check form is active
        3. Check plan limits
        4. Run spam checks
        5. Insert into dynamic table
        6. Insert into form_submission_index
        7. Increment counters

        Returns the submission ID.
        """
        metadata = metadata or {}

        # 1. Lookup form
        result = await self.db.execute(
            select(Form).where(Form.form_key == form_key, Form.deleted_at.is_(None))
        )
        form = result.scalar_one_or_none()
        if not form:
            raise FormNotActiveError("Form not found")
        if not form.is_active:
            raise FormNotActiveError()

        # 2. Lookup project
        project_result = await self.db.execute(
            select(Project).where(Project.id == form.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise FormNotActiveError("Project not found")

        # 3. Origin validation (only when allowed_origins is configured)
        request_origin = metadata.get("_request_origin")
        if request_origin and form.allowed_origins:
            allowed: list[str] = form.allowed_origins if isinstance(form.allowed_origins, list) else []
            if allowed and request_origin not in allowed:
                from server.exceptions import ForbiddenError
                raise ForbiddenError(
                    f"Origin '{request_origin}' is not allowed to submit to this form"
                )
        # Remove the internal _request_origin key before storing metadata
        metadata.pop("_request_origin", None)

        # 4. Check plan limits
        if project.submission_used_this_month >= project.submission_limit_monthly:
            raise PlanLimitError(
                f"Monthly submission limit ({project.submission_limit_monthly}) reached"
            )

        # 4. Spam checks
        spam_score = self._calculate_spam_score(data, metadata, form.spam_protection)
        is_spam = spam_score > 70

        # 5. Generate IDs
        submission_id = uuid.uuid4()
        ip_hash = hashlib.sha256(
            f"{client_ip}:{datetime.now().strftime('%Y-%m-%d')}".encode()
        ).hexdigest()

        # 6. Get current schema version
        version_result = await self.db.execute(
            select(FormSchemaVersion)
            .where(FormSchemaVersion.form_id == form.id)
            .order_by(FormSchemaVersion.version.desc())
            .limit(1)
        )
        schema_version = version_result.scalar_one_or_none()

        # Create initial version if none exists
        if not schema_version:
            schema_version = FormSchemaVersion(
                form_id=form.id,
                version=1,
                schema_snapshot=form.schema,
                created_by=form.created_by,
            )
            self.db.add(schema_version)
            await self.db.flush()

        # 7. Insert into dynamic table (if not spam)
        dynamic_row_id = uuid.uuid4()
        if form.table_created and not is_spam:
            dynamic_row_id = await self.table_service.insert_row(
                table_name=form.table_name,
                submission_id=submission_id,
                schema_version=form.schema_version,
                data=data,
                ip_hash=ip_hash,
                a_b_variant=metadata.get("a_b_variant"),
            )

        # 8. Build data snapshot (first 5 fields)
        data_snapshot = {}
        for i, (key, value) in enumerate(data.items()):
            if i >= 5:
                break
            data_snapshot[key] = str(value)[:200] if value else None

        # 9. Extract contact fields
        email = data.get("email") or data.get("Email")
        phone = data.get("phone") or data.get("Phone") or data.get("mobile")
        name = data.get("name") or data.get("Name") or data.get("full_name")

        # 10. Insert submission index
        submission = FormSubmissionIndex(
            id=submission_id,
            project_id=form.project_id,
            form_id=form.id,
            form_key=form.form_key,
            schema_version_id=schema_version.id,
            dynamic_table_row_id=dynamic_row_id,
            is_spam=is_spam,
            spam_score=spam_score,
            email=str(email) if email else None,
            phone=str(phone) if phone else None,
            name=str(name) if name else None,
            data_snapshot=data_snapshot,
            source_url=metadata.get("source_url"),
            referrer=metadata.get("referrer"),
            device=metadata.get("device"),
            ip_address=client_ip,
            utm_data=metadata.get("utm_data"),
            a_b_variant=metadata.get("a_b_variant"),
        )
        self.db.add(submission)

        # 11. Increment counters
        await self.db.execute(
            update(Form).where(Form.id == form.id).values(
                submission_count=Form.submission_count + 1
            )
        )
        await self.db.execute(
            update(Project).where(Project.id == project.id).values(
                submission_used_this_month=Project.submission_used_this_month + 1
            )
        )

        await self.db.flush()

        logger.info(
            f"Submission processed: form={form_key} spam={is_spam} score={spam_score}"
        )

        return submission_id

    def _calculate_spam_score(
        self,
        data: dict[str, Any],
        metadata: dict[str, Any],
        spam_config: dict[str, Any],
    ) -> int:
        """
        Calculate spam score (0-100) based on multiple signals.
        """
        score = 0

        # Layer 1: Honeypot
        honeypot_field = spam_config.get("honeypot_field", "_gotcha")
        if data.get(honeypot_field):
            score += 100  # Instant spam
            return score

        # Layer 3: Timing check
        started_at = metadata.get("started_at")
        min_time = spam_config.get("min_time_seconds", 2)
        if started_at:
            try:
                elapsed = time.time() - float(started_at)
                if elapsed < min_time:
                    score += 40
            except (ValueError, TypeError):
                pass

        # Layer 4: Content pattern scoring
        all_text = " ".join(str(v) for v in data.values() if v and isinstance(v, str))

        # URL density
        url_count = all_text.count("http://") + all_text.count("https://")
        if url_count > 3:
            score += 20
        elif url_count > 1:
            score += 10

        # Repeated characters
        import re
        if re.search(r"(.)\1{10,}", all_text):
            score += 15

        # Very short content + many URLs = likely spam
        if len(all_text) < 20 and url_count > 0:
            score += 15

        return min(score, 100)
