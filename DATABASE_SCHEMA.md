# 🗄️ FormNest — Database Schema
**Manovratha Tech · Version 2.0 · PostgreSQL 16**

> This schema is deliberately aligned with TREEEX-WBSP's data model for a planned Year 1–2 merger. Shared patterns: multi-tenant projects (= WBSP workspaces), RBAC member roles, tag system, Supabase auth UUIDs, soft deletes, and JSONB metadata fields.
> Columns marked `-- MERGER` are nullable stubs — populated only after the WBSP bridge integration activates.

---

## 📊 Entity Relationship Overview

```
users
  └──▷ project_members (role-based access)
  └──▷ projects (created_by)

projects
  └──▷ project_members
  └──▷ forms
  │     └──▷ form_schema_versions
  │     └──▷ form_submission_index        ← central lead index
  │           └──▷ submission_tag_links   (M2M)
  │           └──▷ ghost_leads            (partial fills, never submitted)
  │           └──▷ [dynamic] fn_proj_{id}_form_{id}  (auto-created per form)
  └──▷ blog_posts
  │     └──▷ programmatic_seo_datasets    (source CSV data)
  └──▷ tags
  │     └──▷ submission_tag_links         (M2M: submissions ↔ tags)
  └──▷ webhooks
  │     └──▷ webhook_delivery_logs
  └──▷ project_integrations              (Notion, GSheets, etc.)
  └──▷ analytics_snapshots
  └──▷ media_files
  └──▷ billing_subscriptions

form_submission_index
  └──▷ submission_tag_links
  └──▷ webhook_delivery_logs
```

---

## 🏗️ Tables Reference

---

### 1. Access Management

---

#### `users`
Global user registry — synced from Supabase Auth. Schema mirrors WBSP `users` exactly.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key — Supabase Auth UID |
| `email` | VARCHAR(255) | NOT NULL | Unique email address |
| `name` | VARCHAR(255) | NULL | Display name |
| `avatar_url` | TEXT | NULL | Profile picture URL |
| `email_verified` | BOOLEAN | NOT NULL | Default: FALSE |
| `is_active` | BOOLEAN | NOT NULL | Default: TRUE |
| `last_login_at` | TIMESTAMPTZ | NULL | Last login timestamp |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `deleted_at` | TIMESTAMPTZ | NULL | Soft delete timestamp |

```sql
CREATE UNIQUE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_active ON users(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_user_deleted ON users(deleted_at) WHERE deleted_at IS NULL;
```

> **🔗 WBSP Alignment:** Identical schema. Same Supabase project → same UUIDs. No migration needed at merger.

---

#### `projects`
Top-level tenant isolation unit. Equivalent to WBSP `workspaces`. Named "projects" for developer friendliness.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `name` | VARCHAR(255) | NOT NULL | Project display name |
| `slug` | VARCHAR(100) | NOT NULL | Unique URL-friendly identifier |
| `api_key` | VARCHAR(40) | NOT NULL | Project API key (`fm_` prefix) |
| `webhook_secret` | UUID | NOT NULL | Outbound webhook HMAC signing key |
| `created_by` | UUID | NOT NULL | FK → users.id |
| `plan` | VARCHAR(20) | NOT NULL | Enum: `free`, `starter`, `growth`, `agency`, `enterprise` |
| `plan_status` | VARCHAR(20) | NOT NULL | Enum: `active`, `past_due`, `cancelled`, `trialing` |
| `submission_limit_monthly` | INTEGER | NOT NULL | Monthly submission quota |
| `submission_used_this_month` | INTEGER | NOT NULL | Default: 0 — reset on billing cycle |
| `form_limit` | INTEGER | NOT NULL | Max forms per project |
| `blog_posts_limit` | INTEGER | NOT NULL | Max blog posts per project |
| `settings` | JSONB | NULL | Custom config (timezone, brand colour, default lang) |
| `custom_domain` | VARCHAR(255) | NULL | Custom blog domain (e.g. blog.client.com) |
| `custom_domain_verified` | BOOLEAN | NOT NULL | Default: FALSE |
| `notification_email` | VARCHAR(255) | NULL | Override email for submission alerts |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `deleted_at` | TIMESTAMPTZ | NULL | Soft delete |
| `wbsp_workspace_id` | UUID | NULL | **MERGER** — FK to WBSP workspaces.id |
| `wbsp_sync_enabled` | BOOLEAN | NOT NULL | Default: FALSE — **MERGER** sync flag |

```sql
CREATE UNIQUE INDEX idx_project_slug ON projects(slug);
CREATE UNIQUE INDEX idx_project_api_key ON projects(api_key);
CREATE INDEX idx_project_created_by ON projects(created_by);
CREATE INDEX idx_project_plan ON projects(plan, plan_status);
CREATE INDEX idx_project_active ON projects(deleted_at) WHERE deleted_at IS NULL;
```

---

#### `project_members`
Links users to projects with roles. Identical RBAC model to WBSP `workspace_members`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `user_id` | UUID | NOT NULL | FK → users.id |
| `role` | VARCHAR(20) | NOT NULL | Enum: `OWNER`, `ADMIN`, `MEMBER`, `VIEWER` |
| `status` | VARCHAR(20) | NOT NULL | Enum: `pending`, `active`, `suspended` |
| `invited_by` | UUID | NULL | FK → users.id |
| `invited_at` | TIMESTAMPTZ | NULL | Invitation timestamp |
| `joined_at` | TIMESTAMPTZ | NULL | Acceptance timestamp |
| `permissions` | JSONB | NULL | Fine-grained role overrides |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE UNIQUE INDEX idx_project_member_unique ON project_members(project_id, user_id);
CREATE INDEX idx_project_member_project ON project_members(project_id);
CREATE INDEX idx_project_member_user ON project_members(user_id);
CREATE INDEX idx_project_member_role ON project_members(role);
```

> **🔗 WBSP Alignment:** Role names (`OWNER`, `ADMIN`, `MEMBER`) are compatible. `VIEWER` → read-only FormNest role (no WBSP equivalent needed at merger).

---

#### `user_notification_settings`
Per-user notification preferences.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `user_id` | UUID | NOT NULL | FK → users.id (unique) |
| `email_new_submission` | BOOLEAN | NOT NULL | Default: TRUE |
| `email_usage_warning` | BOOLEAN | NOT NULL | Default: TRUE |
| `email_weekly_digest` | BOOLEAN | NOT NULL | Default: FALSE |
| `email_marketing` | BOOLEAN | NOT NULL | Default: TRUE |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE UNIQUE INDEX idx_notif_user ON user_notification_settings(user_id);
```

---

### 2. Forms Engine

---

#### `forms`
Form definitions — field schema, embed config, spam protection.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `name` | VARCHAR(255) | NOT NULL | Form display name (e.g. "Contact Us") |
| `form_key` | VARCHAR(40) | NOT NULL | Public embed key (`fm_abc123`) |
| `schema` | JSONB | NOT NULL | Array of field definitions |
| `schema_version` | SMALLINT | NOT NULL | Default: 1 — incremented on schema change |
| `form_type` | VARCHAR(20) | NOT NULL | Enum: `single_page`, `multi_step`, `survey` |
| `steps_config` | JSONB | NULL | Step definitions for multi-step forms |
| `table_name` | VARCHAR(100) | NOT NULL | Auto-generated table: `fn_proj_{id}_form_{id}` |
| `table_created` | BOOLEAN | NOT NULL | Default: FALSE |
| `is_active` | BOOLEAN | NOT NULL | Default: TRUE |
| `submission_count` | INTEGER | NOT NULL | Default: 0 |
| `success_message` | TEXT | NULL | Custom post-submit message |
| `redirect_url` | TEXT | NULL | Redirect URL after submit |
| `allowed_origins` | JSONB | NULL | Allowed CORS origins (NULL = all) |
| `spam_protection` | JSONB | NOT NULL | `{honeypot_field, rate_limit, captcha_enabled, min_time_seconds}` |
| `styling` | JSONB | NULL | Widget theme: `{primary_color, font, border_radius, button_text}` |
| `a_b_test_enabled` | BOOLEAN | NOT NULL | Default: FALSE |
| `a_b_variant_schema` | JSONB | NULL | Variant B schema for A/B test |
| `partial_save_enabled` | BOOLEAN | NOT NULL | Default: TRUE — ghost leads |
| `created_by` | UUID | NOT NULL | FK → users.id |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `deleted_at` | TIMESTAMPTZ | NULL | Soft delete |

**Form Schema JSONB Spec (`schema` column):**
```json
[
  {
    "key": "name",
    "label": "Full Name",
    "type": "text",
    "required": true,
    "placeholder": "e.g. Priya Sharma",
    "validation": { "minLength": 2, "maxLength": 100 },
    "step": 1
  },
  {
    "key": "email",
    "label": "Email Address",
    "type": "email",
    "required": true,
    "step": 1
  },
  {
    "key": "budget",
    "label": "Monthly Budget",
    "type": "select",
    "required": true,
    "options": ["Under ₹10K", "₹10K–₹50K", "₹50K+"],
    "step": 2,
    "conditional": { "show_if": { "field": "service_type", "value": "development" } }
  },
  {
    "key": "message",
    "label": "Tell us about your project",
    "type": "textarea",
    "required": false,
    "validation": { "maxLength": 2000 },
    "step": 3
  }
]
```

**Supported Field Types:** `text`, `email`, `phone`, `number`, `textarea`, `select`, `multiselect`, `checkbox`, `radio`, `date`, `url`, `hidden`, `file` (Phase 2), `rating` (Phase 2)

```sql
CREATE UNIQUE INDEX idx_form_key ON forms(form_key);
CREATE UNIQUE INDEX idx_form_table_name ON forms(table_name);
CREATE INDEX idx_form_project ON forms(project_id);
CREATE INDEX idx_form_active ON forms(project_id, is_active, deleted_at) WHERE deleted_at IS NULL;
```

---

#### `form_schema_versions`
Immutable history of every schema change. Enables submission-to-schema mapping.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `form_id` | UUID | NOT NULL | FK → forms.id |
| `version` | SMALLINT | NOT NULL | Version number |
| `schema_snapshot` | JSONB | NOT NULL | Exact copy of `forms.schema` at this version |
| `change_reason` | VARCHAR(255) | NULL | Optional human note |
| `created_by` | UUID | NOT NULL | FK → users.id |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE UNIQUE INDEX idx_schema_version_unique ON form_schema_versions(form_id, version);
CREATE INDEX idx_schema_version_form ON form_schema_versions(form_id);
```

---

#### `form_submission_index`
Central index of all submissions across all dynamic form tables. The primary table for dashboard queries, analytics, and WBSP bridge.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `form_id` | UUID | NOT NULL | FK → forms.id |
| `form_key` | VARCHAR(40) | NOT NULL | Denormalised for fast lookup |
| `schema_version_id` | UUID | NOT NULL | FK → form_schema_versions.id |
| `dynamic_table_row_id` | UUID | NOT NULL | Row ID in the dynamic table |
| `is_spam` | BOOLEAN | NOT NULL | Default: FALSE |
| `spam_score` | SMALLINT | NOT NULL | Default: 0 (0–100) |
| `email` | VARCHAR(255) | NULL | Extracted from submission (PII — encrypted) |
| `phone` | VARCHAR(20) | NULL | Extracted from submission (PII — encrypted) |
| `name` | VARCHAR(255) | NULL | Extracted from submission |
| `data_snapshot` | JSONB | NOT NULL | First 5 fields as key-value snapshot |
| `source_url` | TEXT | NULL | Page URL where form was submitted |
| `referrer` | TEXT | NULL | HTTP Referrer header |
| `device` | VARCHAR(10) | NULL | Enum: `mobile`, `tablet`, `desktop` |
| `ip_address` | INET | NULL | Client IP (hashed after 30 days) |
| `utm_data` | JSONB | NULL | `{source, medium, campaign, content, term}` |
| `a_b_variant` | VARCHAR(1) | NULL | `A` or `B` if A/B test active |
| `submitted_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `reviewed_at` | TIMESTAMPTZ | NULL | When owner first opened this submission |
| `wbsp_contact_id` | UUID | NULL | **MERGER** — FK to WBSP contacts.id |
| `wbsp_synced_at` | TIMESTAMPTZ | NULL | **MERGER** — timestamp of WBSP sync |

```sql
CREATE INDEX idx_sub_idx_project_time ON form_submission_index(project_id, submitted_at DESC);
CREATE INDEX idx_sub_idx_form_time ON form_submission_index(form_id, submitted_at DESC);
CREATE INDEX idx_sub_idx_email ON form_submission_index(email) WHERE email IS NOT NULL;
CREATE INDEX idx_sub_idx_phone ON form_submission_index(phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_sub_idx_spam ON form_submission_index(project_id, is_spam);
CREATE INDEX idx_sub_idx_utm ON form_submission_index USING GIN (utm_data);
CREATE INDEX idx_sub_idx_unreviewed ON form_submission_index(project_id, reviewed_at)
  WHERE reviewed_at IS NULL AND is_spam = FALSE;
```

> **🔒 PII:** `email` and `phone` must be encrypted at column level (AES-256 via pgcrypto or application layer). Never return plain values in list API responses — mask as `pri***@example.com`.
>
> **🔗 WBSP Bridge:** `wbsp_contact_id` and `wbsp_synced_at` are populated by `BridgeService` when WBSP sync is enabled on the project. The bridge reads `email` and `phone` to create/update WBSP contacts.

---

#### `ghost_leads`
Partial form fills that were never submitted. Captured by `partial_save` endpoint.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `form_id` | UUID | NOT NULL | FK → forms.id |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `fingerprint` | VARCHAR(64) | NOT NULL | Browser fingerprint (SHA256 of IP+UA) |
| `partial_data` | JSONB | NOT NULL | Fields filled so far |
| `email` | VARCHAR(255) | NULL | If email field was reached (PII — encrypted) |
| `phone` | VARCHAR(20) | NULL | If phone field was reached (PII — encrypted) |
| `last_step_reached` | SMALLINT | NULL | For multi-step: last step number |
| `source_url` | TEXT | NULL | Page where partial fill occurred |
| `device` | VARCHAR(10) | NULL | `mobile`, `tablet`, `desktop` |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() + 24h (Redis TTL mirrors this) |
| `converted_at` | TIMESTAMPTZ | NULL | Set when ghost lead completes submission |
| `converted_submission_id` | UUID | NULL | FK → form_submission_index.id |

```sql
CREATE INDEX idx_ghost_form ON ghost_leads(form_id, created_at DESC);
CREATE INDEX idx_ghost_email ON ghost_leads(email) WHERE email IS NOT NULL;
CREATE INDEX idx_ghost_expires ON ghost_leads(expires_at) WHERE converted_at IS NULL;
```

> **Retention:** Hard-delete expired rows (where `expires_at < NOW()` and `converted_at IS NULL`) daily via scheduled job. Converted ghost leads retained for 30 days for analytics.

---

#### `submission_tag_links`
M2M junction: form_submission_index ↔ tags.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `submission_id` | UUID | NOT NULL | FK → form_submission_index.id |
| `tag_id` | UUID | NOT NULL | FK → tags.id |
| `tagged_by` | UUID | NOT NULL | FK → users.id (who added the tag) |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE UNIQUE INDEX idx_sub_tag_unique ON submission_tag_links(submission_id, tag_id);
CREATE INDEX idx_sub_tag_submission ON submission_tag_links(submission_id);
CREATE INDEX idx_sub_tag_tag ON submission_tag_links(tag_id);
```

---

#### `tags`
Reusable labels for lead segmentation. Identical schema to WBSP `tags`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `name` | VARCHAR(50) | NOT NULL | Tag label |
| `color` | VARCHAR(7) | NOT NULL | Hex colour e.g. `#22C55E` |
| `description` | VARCHAR(255) | NULL | Optional description |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE UNIQUE INDEX idx_tag_project_name ON tags(project_id, lower(name));
CREATE INDEX idx_tag_project ON tags(project_id);
```

> **🔗 WBSP Alignment:** Schema is identical to WBSP `tags`. At merger, tags become shared across both products under the unified workspace.

---

### 3. Blog + SEO CMS

---

#### `blog_posts`
Blog post content + SEO metadata. Rendered as public pages.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `title` | VARCHAR(255) | NOT NULL | Post title |
| `slug` | VARCHAR(255) | NOT NULL | URL slug (unique per project) |
| `content_markdown` | TEXT | NOT NULL | Raw Markdown source |
| `content_html` | TEXT | NULL | Rendered HTML (cached) |
| `excerpt` | TEXT | NULL | Auto-generated from first 160 chars if NULL |
| `status` | VARCHAR(20) | NOT NULL | Enum: `draft`, `published`, `archived` |
| `author_id` | UUID | NOT NULL | FK → users.id |
| `published_at` | TIMESTAMPTZ | NULL | Set on first publish |
| `seo_title` | VARCHAR(70) | NULL | SEO title (falls back to `title`) |
| `seo_description` | VARCHAR(160) | NULL | Meta description |
| `seo_keywords` | TEXT[] | NULL | Meta keywords array |
| `og_title` | VARCHAR(70) | NULL | OG title (falls back to `seo_title`) |
| `og_description` | VARCHAR(200) | NULL | OG description |
| `og_image_url` | TEXT | NULL | OG image (auto-generated or uploaded) |
| `canonical_url` | TEXT | NULL | Canonical URL override |
| `schema_markup` | JSONB | NULL | Schema.org JSON-LD blob |
| `reading_time_minutes` | SMALLINT | NULL | Auto-calculated |
| `word_count` | INTEGER | NULL | Auto-calculated |
| `view_count` | INTEGER | NOT NULL | Default: 0 |
| `tags` | TEXT[] | NULL | Simple string tag array for blog categories |
| `is_programmatic` | BOOLEAN | NOT NULL | Default: FALSE — generated by PSeo engine |
| `pse_template_id` | UUID | NULL | FK → programmatic_seo_templates.id |
| `pse_dataset_row_id` | UUID | NULL | FK → programmatic_seo_datasets.id |
| `search_vector` | TSVECTOR | NULL | Full-text search vector (auto-updated via trigger) |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `deleted_at` | TIMESTAMPTZ | NULL | Soft delete |

```sql
CREATE UNIQUE INDEX idx_blog_project_slug ON blog_posts(project_id, slug) WHERE deleted_at IS NULL;
CREATE INDEX idx_blog_project_status ON blog_posts(project_id, status, published_at DESC);
CREATE INDEX idx_blog_published ON blog_posts(published_at DESC) WHERE status = 'published';
CREATE INDEX idx_blog_search ON blog_posts USING GIN (search_vector);
CREATE INDEX idx_blog_programmatic ON blog_posts(project_id, is_programmatic);

-- Auto-update search vector on insert/update
CREATE OR REPLACE FUNCTION update_blog_search_vector() RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.seo_description, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW.content_markdown, '')), 'C');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER blog_search_update
  BEFORE INSERT OR UPDATE OF title, seo_description, content_markdown
  ON blog_posts
  FOR EACH ROW EXECUTE FUNCTION update_blog_search_vector();
```

---

#### `programmatic_seo_templates`
Template definitions for generating bulk SEO pages from data.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `name` | VARCHAR(255) | NOT NULL | Template name |
| `title_template` | VARCHAR(255) | NOT NULL | e.g. `Best {{service}} in {{city}} — 2025 Guide` |
| `content_template` | TEXT | NOT NULL | Markdown template with `{{variable}}` placeholders |
| `seo_description_template` | VARCHAR(200) | NULL | SEO description template |
| `slug_template` | VARCHAR(255) | NOT NULL | e.g. `{{service}}-in-{{city}}` |
| `schema_template` | JSONB | NULL | Schema.org template with variable slots |
| `is_active` | BOOLEAN | NOT NULL | Default: FALSE — activate to trigger generation |
| `generated_count` | INTEGER | NOT NULL | Default: 0 |
| `created_by` | UUID | NOT NULL | FK → users.id |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE INDEX idx_pse_template_project ON programmatic_seo_templates(project_id);
```

---

#### `programmatic_seo_datasets`
CSV data rows used to hydrate PSeo templates.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `template_id` | UUID | NOT NULL | FK → programmatic_seo_templates.id |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `variables` | JSONB | NOT NULL | `{city: "Bangalore", service: "plumber", ...}` |
| `status` | VARCHAR(20) | NOT NULL | Enum: `pending`, `generated`, `failed`, `skipped` |
| `blog_post_id` | UUID | NULL | FK → blog_posts.id (set after generation) |
| `error_message` | TEXT | NULL | Generation error if status=failed |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE INDEX idx_pse_dataset_template ON programmatic_seo_datasets(template_id, status);
CREATE INDEX idx_pse_dataset_post ON programmatic_seo_datasets(blog_post_id);
```

---

### 4. Webhooks & Integrations

---

#### `webhooks`
Outbound webhook configurations per project.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `name` | VARCHAR(100) | NOT NULL | Human-readable name (e.g. "Slack Lead Alert") |
| `url` | TEXT | NOT NULL | Target endpoint URL |
| `secret` | VARCHAR(64) | NOT NULL | HMAC signing secret (stored hashed, never returned) |
| `events` | TEXT[] | NOT NULL | e.g. `{form.submission, form.spam}` |
| `form_id` | UUID | NULL | FK → forms.id (NULL = fires for all project forms) |
| `headers` | JSONB | NULL | Custom headers to include (e.g. Authorization) |
| `is_active` | BOOLEAN | NOT NULL | Default: TRUE |
| `failure_count` | SMALLINT | NOT NULL | Default: 0 — incremented on delivery failure |
| `auto_disabled_at` | TIMESTAMPTZ | NULL | Set if too many failures (auto-disable) |
| `created_by` | UUID | NOT NULL | FK → users.id |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE INDEX idx_webhook_project ON webhooks(project_id);
CREATE INDEX idx_webhook_form ON webhooks(form_id) WHERE form_id IS NOT NULL;
CREATE INDEX idx_webhook_active ON webhooks(project_id, is_active) WHERE is_active = TRUE;
```

---

#### `webhook_delivery_logs`
Per-attempt delivery log for outbound webhooks.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `webhook_id` | UUID | NOT NULL | FK → webhooks.id |
| `submission_id` | UUID | NOT NULL | FK → form_submission_index.id |
| `attempt_number` | SMALLINT | NOT NULL | 1, 2, or 3 |
| `status` | VARCHAR(10) | NOT NULL | Enum: `success`, `failed`, `timeout` |
| `http_status_code` | SMALLINT | NULL | Response status code |
| `response_body` | TEXT | NULL | First 500 chars of response |
| `duration_ms` | INTEGER | NULL | Request duration |
| `error_message` | TEXT | NULL | Error details on failure |
| `attempted_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE INDEX idx_wdl_webhook ON webhook_delivery_logs(webhook_id, attempted_at DESC);
CREATE INDEX idx_wdl_submission ON webhook_delivery_logs(submission_id);
CREATE INDEX idx_wdl_status ON webhook_delivery_logs(status, attempted_at DESC);
```

> **Retention:** Hard-delete rows older than 90 days.

---

#### `project_integrations`
Third-party integration configs (Notion, Google Sheets, Slack, etc.).

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `integration_type` | VARCHAR(30) | NOT NULL | Enum: `notion`, `google_sheets`, `slack`, `airtable`, `zapier` |
| `form_id` | UUID | NULL | FK → forms.id (NULL = project-wide) |
| `is_active` | BOOLEAN | NOT NULL | Default: FALSE |
| `credentials` | JSONB | NOT NULL | Encrypted OAuth tokens / API keys |
| `config` | JSONB | NOT NULL | Mapping config (field → destination column/property) |
| `last_sync_at` | TIMESTAMPTZ | NULL | Last successful sync |
| `last_error` | TEXT | NULL | Last sync error |
| `sync_count` | INTEGER | NOT NULL | Default: 0 |
| `created_by` | UUID | NOT NULL | FK → users.id |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE UNIQUE INDEX idx_integration_project_type_form
  ON project_integrations(project_id, integration_type, coalesce(form_id, '00000000-0000-0000-0000-000000000000'::uuid));
CREATE INDEX idx_integration_project ON project_integrations(project_id);
```

> **🔒 Security:** `credentials` JSONB must be encrypted at rest (AES-256 application layer or pgcrypto). Never log or return raw values. Rotate access tokens before expiry via background job.

---

### 5. Analytics

---

#### `analytics_snapshots`
Pre-aggregated daily/hourly stats per form. Powers the dashboard without expensive GROUP BY queries.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `form_id` | UUID | NULL | FK → forms.id (NULL = project-level rollup) |
| `period` | VARCHAR(10) | NOT NULL | Enum: `hour`, `day`, `week`, `month` |
| `period_start` | TIMESTAMPTZ | NOT NULL | Start of the period |
| `total_submissions` | INTEGER | NOT NULL | Default: 0 |
| `spam_submissions` | INTEGER | NOT NULL | Default: 0 |
| `ghost_leads` | INTEGER | NOT NULL | Default: 0 |
| `converted_ghost_leads` | INTEGER | NOT NULL | Default: 0 |
| `source_breakdown` | JSONB | NULL | `{google: 12, direct: 8, facebook: 3}` |
| `device_breakdown` | JSONB | NULL | `{mobile: 18, desktop: 5}` |
| `utm_breakdown` | JSONB | NULL | `{organic: 10, cpc: 5, social: 7}` |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE UNIQUE INDEX idx_analytics_snapshot_unique
  ON analytics_snapshots(project_id, coalesce(form_id, '00000000-0000-0000-0000-000000000000'::uuid), period, period_start);
CREATE INDEX idx_analytics_project_period ON analytics_snapshots(project_id, period, period_start DESC);
```

---

### 6. Media

---

#### `media_files`
Media file metadata. Files stored in Cloudflare R2.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id |
| `type` | VARCHAR(20) | NOT NULL | Enum: `image`, `document`, `video`, `audio` |
| `storage_key` | TEXT | NOT NULL | Cloudflare R2 object key |
| `public_url` | TEXT | NULL | CDN public URL |
| `file_name` | VARCHAR(255) | NOT NULL | Original filename |
| `file_size` | BIGINT | NOT NULL | Size in bytes |
| `mime_type` | VARCHAR(100) | NOT NULL | MIME type |
| `purpose` | VARCHAR(30) | NOT NULL | Enum: `blog_image`, `form_upload`, `og_image`, `avatar` |
| `uploaded_by` | UUID | NOT NULL | FK → users.id |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `deleted_at` | TIMESTAMPTZ | NULL | Soft delete (also deletes from R2 via cleanup job) |

```sql
CREATE INDEX idx_media_project ON media_files(project_id);
CREATE INDEX idx_media_type_purpose ON media_files(type, purpose);
```

---

### 7. Billing

---

#### `billing_subscriptions`
Razorpay and Stripe subscription tracking.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NOT NULL | FK → projects.id (unique) |
| `user_id` | UUID | NOT NULL | FK → users.id (subscriber) |
| `provider` | VARCHAR(20) | NOT NULL | Enum: `razorpay`, `stripe` |
| `provider_subscription_id` | TEXT | NOT NULL | Provider subscription ID |
| `provider_customer_id` | TEXT | NOT NULL | Provider customer ID |
| `plan` | VARCHAR(20) | NOT NULL | Enum: `starter`, `growth`, `agency`, `enterprise` |
| `billing_cycle` | VARCHAR(10) | NOT NULL | Enum: `monthly`, `annual` |
| `amount_subunit` | INTEGER | NOT NULL | Amount in paise (₹) or cents ($) |
| `currency` | VARCHAR(3) | NOT NULL | `INR` or `USD` |
| `status` | VARCHAR(20) | NOT NULL | Enum: `active`, `past_due`, `cancelled`, `trialing` |
| `trial_ends_at` | TIMESTAMPTZ | NULL | Trial expiry |
| `current_period_start` | TIMESTAMPTZ | NOT NULL | Billing period start |
| `current_period_end` | TIMESTAMPTZ | NOT NULL | Billing period end |
| `cancelled_at` | TIMESTAMPTZ | NULL | Cancellation timestamp |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE UNIQUE INDEX idx_billing_project ON billing_subscriptions(project_id);
CREATE UNIQUE INDEX idx_billing_provider_sub
  ON billing_subscriptions(provider, provider_subscription_id);
CREATE INDEX idx_billing_status ON billing_subscriptions(status);
CREATE INDEX idx_billing_period ON billing_subscriptions(current_period_end) WHERE status = 'active';
```

---

#### `billing_events`
Webhook event log from Razorpay / Stripe. Idempotency guard.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `provider` | VARCHAR(20) | NOT NULL | `razorpay` or `stripe` |
| `event_id` | TEXT | NOT NULL | Provider event ID (idempotency key) |
| `event_type` | VARCHAR(100) | NOT NULL | e.g. `payment.captured`, `subscription.cancelled` |
| `project_id` | UUID | NULL | FK → projects.id |
| `processed` | BOOLEAN | NOT NULL | Default: FALSE |
| `raw_payload` | JSONB | NOT NULL | Full webhook payload |
| `error_message` | TEXT | NULL | Processing error |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

```sql
CREATE UNIQUE INDEX idx_billing_event_id ON billing_events(provider, event_id);
CREATE INDEX idx_billing_event_project ON billing_events(project_id);
CREATE INDEX idx_billing_event_unprocessed ON billing_events(processed, created_at) WHERE processed = FALSE;
```

---

### 8. Audit & Logs

---

#### `api_access_logs`
Lightweight request audit log.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NULL | FK → projects.id |
| `user_id` | UUID | NULL | FK → users.id |
| `method` | VARCHAR(10) | NOT NULL | HTTP method |
| `path` | TEXT | NOT NULL | Request path (sanitised) |
| `status_code` | SMALLINT | NOT NULL | HTTP response status |
| `duration_ms` | INTEGER | NULL | Request duration |
| `ip_address` | INET | NULL | Client IP |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

**Retention:** 30 days. Hard-deleted by scheduled job.

```sql
CREATE INDEX idx_api_log_project ON api_access_logs(project_id, created_at DESC);
CREATE INDEX idx_api_log_time ON api_access_logs(created_at DESC);
```

---

#### `email_logs`
Log of all outbound email attempts.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | NOT NULL | Primary key |
| `project_id` | UUID | NULL | FK → projects.id |
| `user_id` | UUID | NULL | FK → users.id |
| `email_type` | VARCHAR(50) | NOT NULL | e.g. `new_submission`, `weekly_digest` |
| `recipient_email` | VARCHAR(255) | NOT NULL | Destination email |
| `status` | VARCHAR(10) | NOT NULL | Enum: `sent`, `failed`, `bounced` |
| `resend_message_id` | TEXT | NULL | Resend.com message ID |
| `error_message` | TEXT | NULL | Failure details |
| `created_at` | TIMESTAMPTZ | NOT NULL | Default: NOW() |

**Retention:** 60 days.

```sql
CREATE INDEX idx_email_log_project ON email_logs(project_id, created_at DESC);
CREATE INDEX idx_email_log_status ON email_logs(status, created_at DESC);
```

---

## 🔗 Dynamic Table Pattern

For each active form, FormNest executes DDL to create:

```sql
-- Table name: fn_proj_{8_char_id}_form_{8_char_id}
-- Example:    fn_proj_a1b2c3d4_form_e5f6g7h8

CREATE TABLE fn_proj_a1b2c3d4_form_e5f6g7h8 (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id   UUID NOT NULL,          -- FK to form_submission_index.id
    schema_version  SMALLINT NOT NULL,

    -- Dynamic columns generated from form schema:
    name            TEXT,
    email           TEXT,                   -- PII — encrypted
    phone           TEXT,                   -- PII — encrypted
    message         TEXT,
    budget          TEXT,

    -- Always present system columns:
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_hash         VARCHAR(64) NOT NULL,   -- SHA256(ip + daily_salt), never raw IP
    a_b_variant     VARCHAR(1)              -- A or B if test active
);

CREATE INDEX ON fn_proj_a1b2c3d4_form_e5f6g7h8 (submitted_at DESC);
CREATE INDEX ON fn_proj_a1b2c3d4_form_e5f6g7h8 (submission_id);
```

**Managed by:** `FormTableMigrationService`
- **Field addition:** `ALTER TABLE ... ADD COLUMN` (existing rows get NULL)
- **Field rename:** new column added with `_deprecated_` prefix on old one — never dropped immediately
- **Field removal:** `_deprecated_` prefix, column preserved for 90 days
- **Type change:** new column added alongside old one; migration script backfills

---

## 🔢 Enums Reference

### Access / Project
| Enum | Values |
|---|---|
| `ProjectPlan` | `free`, `starter`, `growth`, `agency`, `enterprise` |
| `PlanStatus` | `active`, `past_due`, `cancelled`, `trialing` |
| `MemberRole` | `OWNER`, `ADMIN`, `MEMBER`, `VIEWER` |
| `MemberStatus` | `pending`, `active`, `suspended` |

### Forms
| Enum | Values |
|---|---|
| `FormType` | `single_page`, `multi_step`, `survey` |
| `FieldType` | `text`, `email`, `phone`, `number`, `textarea`, `select`, `multiselect`, `checkbox`, `radio`, `date`, `url`, `hidden`, `file`, `rating` |

### Blog
| Enum | Values |
|---|---|
| `PostStatus` | `draft`, `published`, `archived` |
| `PseoDatasetStatus` | `pending`, `generated`, `failed`, `skipped` |

### Integrations
| Enum | Values |
|---|---|
| `IntegrationType` | `notion`, `google_sheets`, `slack`, `airtable`, `zapier`, `wbsp` |

### Webhooks
| Enum | Values |
|---|---|
| `WebhookEvent` | `form.submission`, `form.spam`, `form.limit_reached`, `ghost.lead_captured` |
| `DeliveryStatus` | `success`, `failed`, `timeout` |

### Billing
| Enum | Values |
|---|---|
| `BillingProvider` | `razorpay`, `stripe` |
| `BillingCycle` | `monthly`, `annual` |
| `SubscriptionStatus` | `active`, `past_due`, `cancelled`, `trialing` |

---

## 🔗 WBSP Merger — Schema Bridge Summary

> **Key Decision (ADR-008):** At merger, WBSP becomes the single application shell. FormNest becomes the **Forms module** inside the WBSP app. Users without a WhatsApp BSP subscription can still log in to the WBSP app and use the Forms module fully. `workspace_id` replaces `project_id` as the universal tenant identifier.

### Identifier Migration: `project_id` → `workspace_id`

The `projects` table is retired at merger. All FormNest tables that reference `project_id` are updated to reference `workspace_id` (WBSP's `workspaces.id`). The `wbsp_workspace_id` stub column (already present in `projects`) makes this a FK swap, not a data migration.

```sql
-- Phase B migration (run once at merger):

-- 1. Migrate projects → workspaces (WBSP handles workspace creation)
--    Each FormNest project gets a new or mapped WBSP workspace row.
--    The wbsp_workspace_id stub is already populated by BridgeService in Phase A.

-- 2. Rename the FK column on all FormNest tables:
ALTER TABLE forms
  RENAME COLUMN project_id TO workspace_id;

ALTER TABLE form_submission_index
  RENAME COLUMN project_id TO workspace_id;

ALTER TABLE ghost_leads
  RENAME COLUMN project_id TO workspace_id;

ALTER TABLE blog_posts
  RENAME COLUMN project_id TO workspace_id;

ALTER TABLE tags
  RENAME COLUMN project_id TO workspace_id;

ALTER TABLE webhooks
  RENAME COLUMN project_id TO workspace_id;

ALTER TABLE project_integrations
  RENAME COLUMN project_id TO workspace_id;

ALTER TABLE analytics_snapshots
  RENAME COLUMN project_id TO workspace_id;

ALTER TABLE media_files
  RENAME COLUMN project_id TO workspace_id;

ALTER TABLE billing_subscriptions
  RENAME COLUMN project_id TO workspace_id;

-- 3. Add workspace_module_flags to WBSP workspaces table:
ALTER TABLE workspaces
  ADD COLUMN forms_module_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN whatsapp_module_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- Migrated FormNest workspaces get forms_module_enabled = TRUE automatically.
-- whatsapp_module_enabled = TRUE only if BSP subscription is active.
```

### Module Flag: Who Sees What

```
workspace.forms_module_enabled = TRUE
  → User can access Forms, Blog, Submissions, Analytics in WBSP app
  → No WhatsApp requirement

workspace.whatsapp_module_enabled = TRUE
  → User can access WhatsApp channels, campaigns, inbox
  → Requires BSP subscription

Both TRUE
  → Full growth loop: form submissions auto-sync to contacts, WhatsApp follow-up available
```

### Pre-Merger Table Map

| FormNest Table | WBSP Table | Merger Action |
|---|---|---|
| `users` | `users` | **No change** — identical schema, same Supabase UUIDs |
| `projects` | `workspaces` | **Retired** — rows migrated to `workspaces`, `project_id` → `workspace_id` everywhere |
| `project_members` | `workspace_members` | **No change** — identical RBAC model, direct copy |
| `tags` | `tags` | **No change** — identical schema → shared tag service |
| `form_submission_index` | contacts (partial) | `BridgeService` dedup-merges `email`/`phone` → WBSP contacts |
| `submission_tag_links` | contact tag M2M | Merge via shared tag IDs |
| `project_integrations` | workspace_integrations | Rename + add `wbsp` integration type |
| Redis queues | Redis queues | Same instance — `fn:` and `wbsp:` key prefixes remain |
| Supabase auth | Supabase auth | **Already shared** — same project, same UUIDs, no re-login |

### `workspaces` Module Flags (Added at Merger in WBSP)

```sql
-- These columns are added to WBSP's workspaces table at merger.
-- FormNest-migrated workspaces: forms_module_enabled = TRUE, whatsapp = FALSE by default.
-- Existing WBSP workspaces: whatsapp_module_enabled = TRUE, forms = FALSE (upgrade prompt).

ALTER TABLE workspaces ADD COLUMN forms_module_enabled     BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE workspaces ADD COLUMN whatsapp_module_enabled  BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE workspaces ADD COLUMN forms_migrated_at        TIMESTAMPTZ NULL;
  -- ^ set when FormNest project migration is complete for this workspace
```

---

## 🔒 Security & Compliance

### PII Columns Requiring Encryption

| Table | Column | Sensitivity | Method |
|---|---|---|---|
| `form_submission_index` | `email`, `phone` | High | AES-256 (pgcrypto or app layer) |
| `ghost_leads` | `email`, `phone` | High | AES-256 |
| Dynamic form tables | `email`, `phone` fields | High | AES-256 |
| `project_integrations` | `credentials` | High | AES-256 app layer |
| `webhooks` | `secret` | Medium | bcrypt hash — never returned |
| `billing_subscriptions` | `provider_customer_id` | Medium | Database TDE |

### Data Retention Schedule

| Table | Retention | Action |
|---|---|---|
| `form_submission_index` | Project-configurable (default 365 days) | Archive + hard delete |
| Dynamic form tables | Same as index (cascade) | Hard delete |
| `ghost_leads` (unconverted) | 24 hours | Hard delete via job |
| `ghost_leads` (converted) | 30 days | Hard delete |
| `api_access_logs` | 30 days | Hard delete |
| `webhook_delivery_logs` | 90 days | Hard delete |
| `email_logs` | 60 days | Hard delete |
| `analytics_snapshots` | hourly: 7 days, daily: 2 years, monthly: forever | Archive hourly/daily |
| IP addresses | 30 days post-submission | Hash to NULL via job |

### DPDP Act 2023 (India) Compliance

- **Data Residency:** All tables in `ap-south-1` (Mumbai) region on hosting provider
- **Consent:** Form widget shows configurable consent checkbox (default: ON with DPDP notice)
- **Erasure Request:** `tasks/erasure.py` — soft delete + 30-day hard delete pipeline
- **Data Export:** `GET /api/v1/projects/{id}/data-export?email={email}` — exports all submissions for a given email address

---

## 📚 Related Documentation

- **[Architecture Overview](ARCHITECTURE.md)** — System design, component flows, tech stack
- **[Project Roadmap](PROJECT_ROADMAP.md)** — Phased development and milestone plan
- **[WBSP Schema](../wbsp/docs/architecture/DATABASE_SCHEMA.md)** — TREEEX-WBSP database reference
- **[API Reference](../api/README.md)** — FastAPI auto-generated endpoint docs

---

*FormNest Database Schema v2.0 · Manovratha Tech · Shashank*
*Designed for TREEEX-WBSP merger compatibility · Target: Year 1–2*
