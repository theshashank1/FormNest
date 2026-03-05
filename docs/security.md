# Security

FormNest is built with security-first defaults. This document covers every
protection layer and how to configure them for your use case.

---

## Authentication security

### JWT tokens
- Issued by Supabase Auth (industry-standard)
- HS256 signed, 7-day expiry
- Refresh tokens enable silent reauthentication
- All token validation happens server-side — no client trust

### API keys
- `fn_` prefixed, 32 random hex characters (128 bits of entropy)
- Never expire until rotated
- Scoped to a single project — cannot access other projects
- Rotation invalidates the old key immediately
- Rotation events are logged for audit

**Best practices:**
- Store API keys in environment variables or a secret manager, never in source code
- Rotate keys on a regular schedule (e.g. every 90 days) or immediately after a breach
- Use separate API keys per environment (dev / staging / production)

---

## Transport security

- All API traffic must use **HTTPS** — HTTP requests are rejected in production
- TLS 1.2 minimum (TLS 1.3 preferred)
- HSTS headers set on all responses

---

## CORS

Cross-Origin Resource Sharing is configured at two levels:

### 1. API-level CORS (server-wide)

The API server allows requests from:
- Your configured `CLIENT_URL` environment variable
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (Next.js dev server)

Set additional origins in `CLIENT_URL` or extend the list in `server/main.py`.

### 2. Per-form origin allowlist

You can restrict which websites are allowed to **submit** to a specific form using
`allowed_origins`:

```bash
curl -X PATCH https://api.formnest.in/api/v1/projects/<pid>/forms/<fid> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "allowed_origins": [
      "https://mysite.com",
      "https://www.mysite.com",
      "https://staging.mysite.com"
    ]
  }'
```

When set, submissions from any other `Origin` receive `403 Forbidden`.
When `allowed_origins` is `null` (default), submissions from any origin are accepted.

---

## Rate limiting

### Submission rate limit

The public submit endpoint (`POST /submit/{form_key}`) enforces:

- **5 requests per minute** per IP address per form key
- Uses Redis sliding-window counter
- Returns `429 Too Many Requests` when exceeded
- Degrades gracefully when Redis is unavailable (falls back to spam scoring)

You can adjust the per-form rate limit via `spam_protection.rate_limit`:

```json
{
  "spam_protection": {
    "rate_limit": 10
  }
}
```

---

## Spam protection

Every submission runs through a multi-layer spam filter:

| Layer | Signal | Score |
|-------|--------|-------|
| Honeypot | Hidden `_gotcha` field filled | +100 (instant reject) |
| Timing | Submitted in < `min_time_seconds` | +40 |
| URL density | > 3 URLs in content | +20 |
| URL density | > 1 URL in content | +10 |
| Repeated chars | 10+ identical consecutive characters | +15 |
| Short + URLs | < 20 chars + any URL | +15 |

Submissions with **total score > 70** are marked as spam.
They are stored but hidden from the default dashboard view.
Spam submissions can be reviewed in the **Spam** tab and manually approved.

### Honeypot field

The `_gotcha` hidden field (name configurable via `spam_protection.honeypot_field`)
is invisible to humans but filled by most bots. Include it in your custom forms:

```html
<!-- This field is intentionally hidden — do not remove -->
<input type="text" name="_gotcha" style="display:none" tabindex="-1" aria-hidden="true" />
```

The iframe embed includes this automatically.

---

## Data security

### IP address handling

Client IP addresses are:
- **Hashed** (SHA-256 with a daily salt) before storage in the dynamic form table
- Stored in plain text in `form_submission_index` for abuse investigation (internal only)
- Never exposed in API responses

### Soft deletion

Deleting a form is a **soft delete** — the record is marked `deleted_at` and made
inactive. The underlying submission data table is preserved.

This prevents accidental permanent data loss. Hard deletion can be requested via
support if needed.

### Sensitive field masking

In **list** responses, `email` and `phone` fields are partially masked:
- `alice@example.com` → `alice@e***.com`

Fetch the **detail** endpoint to see the full value (requires authentication).

---

## Plan limits

| Limit | Free | Starter | Growth |
|-------|------|---------|--------|
| Forms per project | 3 | 10 | 50 |
| Submissions/month | 100 | 1,000 | 10,000 |

Exceeding limits returns `403 PLAN_LIMIT_EXCEEDED`.

---

## Environment variables

Sensitive configuration is loaded from environment variables. See `.env.example`
for the full list. Critical variables for production:

| Variable | Required | Notes |
|----------|----------|-------|
| `SECRET_KEY` | ✅ | 32+ random chars, used for token signing |
| `SUPABASE_URL` | ✅ | Your Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon key |
| `SUPABASE_SECRET_KEY` | ✅ | Supabase service role key (server-only) |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `HCAPTCHA_SECRET` | optional | Enable captcha on forms |
| `SENTRY_DSN` | optional | Error monitoring |

**Never commit `.env` files to source control.**
Use `.env.example` as the template and document changes there.

---

## Reporting security vulnerabilities

Found a security issue? Please **do not open a public GitHub issue**.
Email `security@formnest.in` with:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact

We aim to respond within 24 hours and patch critical issues within 72 hours.
