# Authentication

FormNest supports two authentication mechanisms. Choose the one that fits your use case.

---

## 1. JWT Bearer Tokens (interactive / frontend)

Tokens are issued by Supabase Auth and expire after **7 days** by default.

### Sign up

```http
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "you@example.com",
  "password": "strongpassword123",
  "name": "Your Name"
}
```

> `name` is optional — defaults to the email address when omitted.

**Response `200 OK`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "v1.refresh...",
  "expires_in": 604800
}
```

### Sign in

```http
POST /api/v1/auth/signin
Content-Type: application/json

{
  "email": "you@example.com",
  "password": "strongpassword123"
}
```

**Response `200 OK`:** Same shape as signup.

### Refresh a token

Access tokens expire. Use the refresh token to get a new pair without re-entering credentials.

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "v1.refresh..."
}
```

### Get current user

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "email": "you@example.com",
  "name": "Your Name",
  "email_verified": true,
  "created_at": "2025-01-01T00:00:00"
}
```

### Using the token

Include the token in the `Authorization` header for every authenticated request:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## 2. API Keys (server-to-server / CLI)

API keys are project-scoped and never expire (until rotated). They are ideal for:

- Backend services submitting internal forms
- CLI scripts and CI/CD pipelines
- Webhooks and integrations

### Get your API key

```http
GET /api/v1/projects/{project_id}/api-key
Authorization: Bearer <access_token>
```

**Response `200 OK`:**
```json
{
  "api_key": "fn_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

The API key prefix `fn_` identifies it as a FormNest project key.

### Using the API key

Include it in the `X-API-Key` header:

```http
X-API-Key: fn_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**Example — list submissions with an API key:**
```bash
curl https://api.formnest.in/api/v1/projects/<project_id>/forms/<form_id>/submissions \
  -H "X-API-Key: fn_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

### Rotate your API key

If a key is compromised, rotate it immediately. The old key is invalidated at once.

```http
POST /api/v1/projects/{project_id}/api-key/rotate
Authorization: Bearer <access_token>
```

**Response `200 OK`:**
```json
{
  "api_key": "fn_newkeyhere..."
}
```

> ⚠️ Update all integrations using the old key before rotating.

---

## Public endpoints (no auth required)

The following endpoints are **always public** — they only need a `form_key`:

| Endpoint | Description |
|----------|-------------|
| `GET /f/{form_key}` | Fetch form schema for rendering |
| `POST /submit/{form_key}` | Submit form data |
| `GET /embed/{form_key}` | Get embed integration code |
| `GET /embed/{form_key}/iframe` | Standalone iframe-ready HTML page |

---

## Error responses

| Status | Code | Meaning |
|--------|------|---------|
| `401` | `UNAUTHORIZED` | Missing / invalid token or API key |
| `403` | `FORBIDDEN` | Token is valid but lacks permission |

**Example error:**
```json
{
  "error": "UNAUTHORIZED",
  "detail": "Invalid or expired token"
}
```
