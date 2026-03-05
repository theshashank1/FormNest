"""Initial schema — all FormNest tables

Revision ID: 0001
Revises:
Create Date: 2026-03-05 12:00:00.000000

Creates all tables defined in the ORM models:
  users, projects, project_members, user_notification_settings,
  tags, forms, form_schema_versions,
  form_submission_index, ghost_leads, submission_tag_links,
  programmatic_seo_templates, blog_posts, programmatic_seo_datasets,
  webhooks, webhook_delivery_logs,
  project_integrations, analytics_snapshots, media_files,
  billing_subscriptions, billing_events,
  api_access_logs, email_logs
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_user_email", "users", ["email"])
    op.create_index("idx_user_active", "users", ["is_active"])
    op.create_index("idx_user_deleted", "users", ["deleted_at"])

    # ------------------------------------------------------------------
    # projects
    # ------------------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("api_key", sa.String(40), nullable=False),
        sa.Column("webhook_secret", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("plan_status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "submission_limit_monthly", sa.Integer(), nullable=False, server_default="100"
        ),
        sa.Column(
            "submission_used_this_month", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("form_limit", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("blog_posts_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("custom_domain", sa.String(255), nullable=True),
        sa.Column(
            "custom_domain_verified", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("notification_email", sa.String(255), nullable=True),
        sa.Column("wbsp_workspace_id", sa.Uuid(), nullable=True),
        sa.Column(
            "wbsp_sync_enabled", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_key"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("webhook_secret"),
    )
    op.create_index("idx_project_slug", "projects", ["slug"])
    op.create_index("idx_project_api_key", "projects", ["api_key"])
    op.create_index("idx_project_created_by", "projects", ["created_by"])
    op.create_index("idx_project_plan", "projects", ["plan", "plan_status"])
    op.create_index("idx_project_active", "projects", ["deleted_at"])

    # ------------------------------------------------------------------
    # project_members
    # ------------------------------------------------------------------
    op.create_table(
        "project_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="MEMBER"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("invited_by", sa.Uuid(), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "permissions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_project_member_unique",
        "project_members",
        ["project_id", "user_id"],
        unique=True,
    )
    op.create_index("idx_project_member_project", "project_members", ["project_id"])
    op.create_index("idx_project_member_user", "project_members", ["user_id"])
    op.create_index("idx_project_member_role", "project_members", ["role"])

    # ------------------------------------------------------------------
    # user_notification_settings
    # ------------------------------------------------------------------
    op.create_table(
        "user_notification_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "email_new_submission", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "email_usage_warning", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "email_weekly_digest", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("email_marketing", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("idx_notif_user", "user_notification_settings", ["user_id"])

    # ------------------------------------------------------------------
    # tags
    # ------------------------------------------------------------------
    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#22C55E"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tag_project_name", "tags", ["project_id", "name"], unique=True
    )
    op.create_index("idx_tag_project", "tags", ["project_id"])

    # ------------------------------------------------------------------
    # programmatic_seo_templates  (blog_posts FKs here, so create first)
    # ------------------------------------------------------------------
    op.create_table(
        "programmatic_seo_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title_template", sa.String(255), nullable=False),
        sa.Column("content_template", sa.Text(), nullable=False),
        sa.Column("seo_description_template", sa.String(200), nullable=True),
        sa.Column("slug_template", sa.String(255), nullable=False),
        sa.Column("schema_template", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("generated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pse_template_project", "programmatic_seo_templates", ["project_id"])

    # ------------------------------------------------------------------
    # blog_posts
    # ------------------------------------------------------------------
    op.create_table(
        "blog_posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=False), nullable=True),
        # SEO
        sa.Column("seo_title", sa.String(70), nullable=True),
        sa.Column("seo_description", sa.String(160), nullable=True),
        sa.Column(
            "seo_keywords", postgresql.ARRAY(sa.Text()), nullable=True
        ),
        sa.Column("og_title", sa.String(70), nullable=True),
        sa.Column("og_description", sa.String(200), nullable=True),
        sa.Column("og_image_url", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("schema_markup", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Stats
        sa.Column("reading_time_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
        # PSeo
        sa.Column("is_programmatic", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("pse_template_id", sa.Uuid(), nullable=True),
        sa.Column("pse_dataset_row_id", sa.Uuid(), nullable=True),
        # Full-text search
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        # Timestamps & soft-delete
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pse_template_id"],
            ["programmatic_seo_templates.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_blog_project_slug", "blog_posts", ["project_id", "slug"], unique=True
    )
    op.create_index(
        "idx_blog_project_status",
        "blog_posts",
        ["project_id", "status", "published_at"],
    )
    op.create_index("idx_blog_published", "blog_posts", ["published_at"])
    op.create_index(
        "idx_blog_programmatic", "blog_posts", ["project_id", "is_programmatic"]
    )

    # ------------------------------------------------------------------
    # programmatic_seo_datasets
    # ------------------------------------------------------------------
    op.create_table(
        "programmatic_seo_datasets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("variables", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("blog_post_id", sa.Uuid(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(
            ["blog_post_id"], ["blog_posts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["programmatic_seo_templates.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_pse_dataset_template",
        "programmatic_seo_datasets",
        ["template_id", "status"],
    )
    op.create_index(
        "idx_pse_dataset_post", "programmatic_seo_datasets", ["blog_post_id"]
    )

    # ------------------------------------------------------------------
    # forms
    # ------------------------------------------------------------------
    op.create_table(
        "forms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("form_key", sa.String(40), nullable=False),
        sa.Column("schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("form_type", sa.String(20), nullable=False, server_default="single_page"),
        sa.Column(
            "steps_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("table_created", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("submission_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_message", sa.Text(), nullable=True),
        sa.Column("redirect_url", sa.Text(), nullable=True),
        sa.Column(
            "allowed_origins", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "spam_protection",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(
                """'{"honeypot_field": "_gotcha", "rate_limit": 5, """
                """"captcha_enabled": false, "min_time_seconds": 2}'::jsonb"""
            ),
        ),
        sa.Column("styling", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "a_b_test_enabled", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "a_b_variant_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "partial_save_enabled", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("form_key"),
        sa.UniqueConstraint("table_name"),
    )
    op.create_index("idx_form_key", "forms", ["form_key"])
    op.create_index("idx_form_table_name", "forms", ["table_name"])
    op.create_index("idx_form_project", "forms", ["project_id"])
    op.create_index("idx_form_active", "forms", ["project_id", "is_active", "deleted_at"])

    # ------------------------------------------------------------------
    # form_schema_versions
    # ------------------------------------------------------------------
    op.create_table(
        "form_schema_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.SmallInteger(), nullable=False),
        sa.Column(
            "schema_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("change_reason", sa.String(255), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["form_id"], ["forms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_schema_version_unique",
        "form_schema_versions",
        ["form_id", "version"],
        unique=True,
    )
    op.create_index("idx_schema_version_form", "form_schema_versions", ["form_id"])

    # ------------------------------------------------------------------
    # form_submission_index
    # ------------------------------------------------------------------
    op.create_table(
        "form_submission_index",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("form_key", sa.String(40), nullable=False),
        sa.Column("schema_version_id", sa.Uuid(), nullable=False),
        sa.Column("dynamic_table_row_id", sa.Uuid(), nullable=False),
        sa.Column("is_spam", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("spam_score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("data_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("device", sa.String(10), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("utm_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("a_b_variant", sa.String(1), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("wbsp_contact_id", sa.Uuid(), nullable=True),
        sa.Column("wbsp_synced_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["form_id"], ["forms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["schema_version_id"], ["form_schema_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_sub_idx_project_time",
        "form_submission_index",
        ["project_id", "submitted_at"],
    )
    op.create_index(
        "idx_sub_idx_form_time",
        "form_submission_index",
        ["form_id", "submitted_at"],
    )
    op.create_index("idx_sub_idx_email", "form_submission_index", ["email"])
    op.create_index("idx_sub_idx_phone", "form_submission_index", ["phone"])
    op.create_index(
        "idx_sub_idx_spam", "form_submission_index", ["project_id", "is_spam"]
    )

    # ------------------------------------------------------------------
    # ghost_leads
    # ------------------------------------------------------------------
    op.create_table(
        "ghost_leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("partial_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("last_step_reached", sa.SmallInteger(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("device", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("converted_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("converted_submission_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["converted_submission_id"],
            ["form_submission_index.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["form_id"], ["forms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ghost_form", "ghost_leads", ["form_id", "created_at"])
    op.create_index("idx_ghost_email", "ghost_leads", ["email"])
    op.create_index("idx_ghost_expires", "ghost_leads", ["expires_at"])

    # ------------------------------------------------------------------
    # submission_tag_links
    # ------------------------------------------------------------------
    op.create_table(
        "submission_tag_links",
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("tagged_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["form_submission_index.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tagged_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("submission_id", "tag_id"),
    )
    op.create_index("idx_sub_tag_submission", "submission_tag_links", ["submission_id"])
    op.create_index("idx_sub_tag_tag", "submission_tag_links", ["tag_id"])

    # ------------------------------------------------------------------
    # webhooks
    # ------------------------------------------------------------------
    op.create_table(
        "webhooks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column("events", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=True),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("failure_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("auto_disabled_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["form_id"], ["forms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_webhook_project", "webhooks", ["project_id"])
    op.create_index("idx_webhook_form", "webhooks", ["form_id"])
    op.create_index("idx_webhook_active", "webhooks", ["project_id", "is_active"])

    # ------------------------------------------------------------------
    # webhook_delivery_logs
    # ------------------------------------------------------------------
    op.create_table(
        "webhook_delivery_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("webhook_id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("http_status_code", sa.SmallInteger(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["form_submission_index.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_wdl_webhook", "webhook_delivery_logs", ["webhook_id", "attempted_at"]
    )
    op.create_index("idx_wdl_submission", "webhook_delivery_logs", ["submission_id"])
    op.create_index(
        "idx_wdl_status", "webhook_delivery_logs", ["status", "attempted_at"]
    )

    # ------------------------------------------------------------------
    # project_integrations
    # ------------------------------------------------------------------
    op.create_table(
        "project_integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("integration_type", sa.String(30), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("credentials", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sync_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["form_id"], ["forms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_integration_project", "project_integrations", ["project_id"])

    # ------------------------------------------------------------------
    # analytics_snapshots
    # ------------------------------------------------------------------
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), nullable=True),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=False), nullable=False),
        sa.Column("total_submissions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spam_submissions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ghost_leads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "converted_ghost_leads", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "source_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "device_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "utm_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["form_id"], ["forms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_analytics_project_period",
        "analytics_snapshots",
        ["project_id", "period", "period_start"],
    )

    # ------------------------------------------------------------------
    # media_files
    # ------------------------------------------------------------------
    op.create_table(
        "media_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("public_url", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_media_project", "media_files", ["project_id"])
    op.create_index("idx_media_type_purpose", "media_files", ["type", "purpose"])

    # ------------------------------------------------------------------
    # billing_subscriptions
    # ------------------------------------------------------------------
    op.create_table(
        "billing_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_subscription_id", sa.Text(), nullable=False),
        sa.Column("provider_customer_id", sa.Text(), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("billing_cycle", sa.String(10), nullable=False),
        sa.Column("amount_subunit", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=False), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=False), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index("idx_billing_project", "billing_subscriptions", ["project_id"])
    op.create_index(
        "idx_billing_provider_sub",
        "billing_subscriptions",
        ["provider", "provider_subscription_id"],
        unique=True,
    )
    op.create_index("idx_billing_status", "billing_subscriptions", ["status"])

    # ------------------------------------------------------------------
    # billing_events
    # ------------------------------------------------------------------
    op.create_table(
        "billing_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_billing_event_id",
        "billing_events",
        ["provider", "event_id"],
        unique=True,
    )
    op.create_index("idx_billing_event_project", "billing_events", ["project_id"])
    op.create_index(
        "idx_billing_event_unprocessed",
        "billing_events",
        ["processed", "created_at"],
    )

    # ------------------------------------------------------------------
    # api_access_logs
    # ------------------------------------------------------------------
    op.create_table(
        "api_access_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("status_code", sa.SmallInteger(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_api_log_project", "api_access_logs", ["project_id", "created_at"]
    )
    op.create_index("idx_api_log_time", "api_access_logs", ["created_at"])

    # ------------------------------------------------------------------
    # email_logs
    # ------------------------------------------------------------------
    op.create_table(
        "email_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("email_type", sa.String(50), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("resend_message_id", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_email_log_project", "email_logs", ["project_id", "created_at"]
    )
    op.create_index("idx_email_log_status", "email_logs", ["status", "created_at"])


def downgrade() -> None:
    # Drop in reverse dependency order (leaves before roots)
    op.drop_table("email_logs")
    op.drop_table("api_access_logs")
    op.drop_table("billing_events")
    op.drop_table("billing_subscriptions")
    op.drop_table("media_files")
    op.drop_table("analytics_snapshots")
    op.drop_table("project_integrations")
    op.drop_table("webhook_delivery_logs")
    op.drop_table("webhooks")
    op.drop_table("submission_tag_links")
    op.drop_table("ghost_leads")
    op.drop_table("form_submission_index")
    op.drop_table("form_schema_versions")
    op.drop_table("forms")
    op.drop_table("programmatic_seo_datasets")
    op.drop_table("blog_posts")
    op.drop_table("programmatic_seo_templates")
    op.drop_table("tags")
    op.drop_table("user_notification_settings")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("users")
