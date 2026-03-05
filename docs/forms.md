# Forms API

All form management endpoints require authentication — either a **JWT Bearer token**
or an **`X-API-Key`** header. See [auth.md](./auth.md) for details.

Base path: `/api/v1/projects/{project_id}/forms`

---

## Field types

| Type | PostgreSQL column | Notes |
|------|-------------------|-------|
| `text` | `TEXT` | Plain text input |
| `email` | `TEXT` | Validated as email |
| `phone` | `TEXT` | Stored as string |
| `number` | `NUMERIC` | Numeric value |
| `textarea` | `TEXT` | Multi-line text |
| `select` | `TEXT` | Single option from list |
| `multiselect` | `TEXT[]` | Multiple options |
| `checkbox` | `BOOLEAN` | true / false |
| `radio` | `TEXT` | Single option |
| `date` | `DATE` | ISO 8601 date |
| `url` | `TEXT` | URL string |
| `hidden` | `TEXT` | Not shown to user |
| `file` | `TEXT` | File URL after upload |
| `rating` | `SMALLINT` | Numeric rating |

---

## Create a form

```http
POST /api/v1/projects/{project_id}/forms
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Contact Form",
  "schema": [
    {
      "key": "name",
      "label": "Full Name",
      "type": "text",
      "required": true,
      "placeholder": "Alice Smith"
    },
    {
      "key": "email",
      "label": "Email Address",
      "type": "email",
      "required": true
    },
    {
      "key": "department",
      "label": "Department",
      "type": "select",
      "options": ["Sales", "Support", "Engineering"]
    },
    {
      "key": "message",
      "label": "Message",
      "type": "textarea",
      "required": false
    }
  ],
  "success_message": "Thanks! We'll be in touch within 24 hours.",
  "redirect_url": null,
  "spam_protection": {
    "honeypot_field": "_gotcha",
    "rate_limit": 5,
    "min_time_seconds": 2
  }
}
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "name": "Contact Form",
  "form_key": "fm_a1b2c3d4e5f6",
  "schema": [...],
  "schema_version": 1,
  "form_type": "single_page",
  "table_name": "fn_proj_a1b2c3d4_form_e5f6g7h8",
  "table_created": true,
  "is_active": true,
  "submission_count": 0,
  "success_message": "Thanks! We'll be in touch within 24 hours.",
  "redirect_url": null,
  "spam_protection": {...},
  "styling": null,
  "partial_save_enabled": true,
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

The `form_key` is the public identifier you share with submitters (e.g. embed in your site).
Each form gets its own PostgreSQL table (`table_name`) for maximum query performance.

---

## List forms

```http
GET /api/v1/projects/{project_id}/forms
Authorization: Bearer <token>
```

**Response `200 OK`:**
```json
{
  "forms": [...],
  "total": 3
}
```

---

## Get a form

```http
GET /api/v1/projects/{project_id}/forms/{form_id}
Authorization: Bearer <token>
```

---

## Update a form

Partial updates — send only the fields you want to change.
Adding new schema fields automatically alters the underlying PostgreSQL table.

```http
PATCH /api/v1/projects/{project_id}/forms/{form_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Name",
  "is_active": false,
  "allowed_origins": ["https://mysite.com", "https://staging.mysite.com"],
  "schema": [
    {"key": "name",  "label": "Name",  "type": "text",  "required": true},
    {"key": "email", "label": "Email", "type": "email", "required": true},
    {"key": "phone", "label": "Phone", "type": "phone"}
  ]
}
```

> When you update `schema`, a new **schema version** is saved automatically.
> Existing columns are never dropped — only new columns are added.

---

## Delete a form

Soft-deletes the form. The form immediately stops accepting new submissions.
Data is preserved for 30 days and can be recovered by support.

```http
DELETE /api/v1/projects/{project_id}/forms/{form_id}
Authorization: Bearer <token>
```

**Response `204 No Content`**

---

## Spam protection

Every form has a `spam_protection` config object:

```json
{
  "honeypot_field": "_gotcha",
  "rate_limit": 5,
  "captcha_enabled": false,
  "min_time_seconds": 2
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `honeypot_field` | `_gotcha` | Hidden field name. Bots fill it; humans don't. |
| `rate_limit` | `5` | Max submissions per minute per IP |
| `captcha_enabled` | `false` | Enable hCaptcha (requires `HCAPTCHA_SECRET` env var) |
| `min_time_seconds` | `2` | Minimum seconds between page load and submit |

---

## Origin allowlist

To restrict which websites can submit to your form, set `allowed_origins`:

```http
PATCH /api/v1/projects/{project_id}/forms/{form_id}
Content-Type: application/json

{
  "allowed_origins": ["https://mysite.com", "https://www.mysite.com"]
}
```

When set, the `Origin` request header is validated on every submission.
Requests from unlisted origins receive `403 Forbidden`.

Leave `allowed_origins` as `null` (default) to accept submissions from anywhere.

---

## Multi-step forms

Set `form_type: "multi_step"` and add a `step` index to each field:

```json
{
  "name": "Onboarding Wizard",
  "form_type": "multi_step",
  "schema": [
    {"key": "name",    "label": "Name",    "type": "text",  "step": 1},
    {"key": "email",   "label": "Email",   "type": "email", "step": 1},
    {"key": "company", "label": "Company", "type": "text",  "step": 2},
    {"key": "role",    "label": "Role",    "type": "select","step": 2,
     "options": ["Developer", "Designer", "Manager"]}
  ],
  "steps_config": {
    "titles": ["Personal Info", "Company Info"],
    "show_progress": true
  }
}
```

---

## Error responses

| Status | Code | Meaning |
|--------|------|---------|
| `404` | `NOT_FOUND` | Form not found or not in this project |
| `403` | `PLAN_LIMIT_EXCEEDED` | Form limit for your plan reached |
| `422` | `VALIDATION_ERROR` | Invalid request body |
