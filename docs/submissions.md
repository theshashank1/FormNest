# Submissions API

FormNest has two categories of submission endpoints:

1. **Public** — no authentication, anyone with a `form_key` can submit
2. **Authenticated** — JWT or API key required, for reading/managing submissions

---

## Public: Submit a form

```http
POST /submit/{form_key}
Content-Type: application/json

{
  "data": {
    "name": "Alice",
    "email": "alice@example.com",
    "message": "Hello from the docs!"
  },
  "metadata": {
    "source_url": "https://mysite.com/contact",
    "referrer": "https://google.com",
    "device": "desktop",
    "utm_data": {
      "utm_source": "google",
      "utm_medium": "cpc",
      "utm_campaign": "spring2025"
    },
    "started_at": 1704067200.0
  }
}
```

**Response `202 Accepted`:**
```json
{
  "submission_id": "uuid",
  "message": "Submission received"
}
```

The `202 Accepted` status means the submission was queued for processing.

### Metadata fields

| Field | Type | Description |
|-------|------|-------------|
| `source_url` | string | Full URL of the page the form was on |
| `referrer` | string | HTTP Referer header value |
| `device` | string | `desktop`, `mobile`, or `tablet` |
| `utm_data` | object | UTM tracking parameters |
| `started_at` | float | Unix timestamp when user first interacted (used for timing spam check) |

### Rate limiting

- **5 submissions per minute** per IP address per form key
- Returns `429 Too Many Requests` when exceeded
- Retry after the window expires (check `Retry-After` header)

### Spam detection

Spam scoring is automatic and transparent:

| Signal | Score |
|--------|-------|
| Honeypot field filled | +100 (instant reject) |
| Submission in < `min_time_seconds` | +40 |
| More than 3 URLs in content | +20 |
| More than 1 URL in content | +10 |
| Repeated characters (10+) | +15 |
| Short content + URLs | +15 |

Submissions with score > 70 are marked as spam and hidden from the default dashboard view.
They are stored and can be reviewed in the **Spam** tab.

### Error responses

| Status | Code | Meaning |
|--------|------|---------|
| `410` | `FORM_NOT_ACTIVE` | Form is paused or deleted |
| `429` | `RATE_LIMIT_EXCEEDED` | Too many requests from this IP |
| `403` | `FORBIDDEN` | Request origin not in `allowed_origins` |
| `403` | `PLAN_LIMIT_EXCEEDED` | Monthly submission limit reached |

---

## List submissions (authenticated)

```http
GET /api/v1/projects/{project_id}/forms/{form_id}/submissions
Authorization: Bearer <token>

Query params:
  page       int  default=1
  page_size  int  default=20, max=100
  is_spam    bool default=false
```

**Response `200 OK`:**
```json
{
  "submissions": [
    {
      "id": "uuid",
      "form_id": "uuid",
      "form_key": "fm_a1b2c3d4e5f6",
      "is_spam": false,
      "spam_score": 0,
      "name": "Alice",
      "email": "alice@e***.com",
      "phone": null,
      "data_snapshot": {
        "name": "Alice",
        "email": "alice@example.com",
        "message": "Hello!"
      },
      "source_url": "https://mysite.com/contact",
      "referrer": null,
      "device": "desktop",
      "utm_data": null,
      "submitted_at": "2025-01-01T12:00:00",
      "reviewed_at": null
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

> **Note:** `email` and `phone` are partially masked in list responses.
> Fetch the submission detail to see the full value.

---

## Get submission detail (authenticated)

Returns the full submission including all fields stored in the dynamic table.
First access automatically marks the submission as reviewed.

```http
GET /api/v1/projects/{project_id}/forms/{form_id}/submissions/{submission_id}
Authorization: Bearer <token>
```

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "form_id": "uuid",
  "form_key": "fm_a1b2c3d4e5f6",
  "is_spam": false,
  "spam_score": 0,
  "name": "Alice",
  "email": "alice@example.com",
  "phone": null,
  "data_snapshot": {...},
  "source_url": "https://mysite.com/contact",
  "referrer": null,
  "device": "desktop",
  "utm_data": null,
  "submitted_at": "2025-01-01T12:00:00",
  "reviewed_at": "2025-01-01T12:05:00",
  "full_data": {
    "name": "Alice",
    "email": "alice@example.com",
    "department": "Engineering",
    "message": "Hello from the docs!"
  }
}
```

---

## Using an API key

All authenticated endpoints accept `X-API-Key` in place of a Bearer token:

```bash
# List submissions using an API key
curl "https://api.formnest.in/api/v1/projects/<project_id>/forms/<form_id>/submissions" \
  -H "X-API-Key: fn_a1b2c3d4e5f6..."

# Get submission detail
curl "https://api.formnest.in/api/v1/projects/<project_id>/forms/<form_id>/submissions/<submission_id>" \
  -H "X-API-Key: fn_a1b2c3d4e5f6..."
```

---

## View spam submissions

```http
GET /api/v1/projects/{project_id}/forms/{form_id}/submissions?is_spam=true
Authorization: Bearer <token>
```

---

## Pagination

```bash
# Page 2, 50 per page
GET /submissions?page=2&page_size=50
```

| Param | Default | Max |
|-------|---------|-----|
| `page` | `1` | — |
| `page_size` | `20` | `100` |
