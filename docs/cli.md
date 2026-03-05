# CLI & Server-to-Server Integration

FormNest's REST API is designed to work beautifully from the command line, CI/CD
pipelines, and any backend language. This guide covers common patterns using `curl`,
shell scripts, Python, and Node.js.

---

## Authentication for CLI

Server-side code should use **API keys** (project-scoped, never expire until rotated)
rather than JWT tokens.

Get your API key from the dashboard or via API:

```bash
curl https://api.formnest.in/api/v1/projects/<project_id>/api-key \
  -H "Authorization: Bearer <jwt_token>"
```

Store it in an environment variable:

```bash
export FORMNEST_API_KEY="fn_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
export FORMNEST_PROJECT_ID="uuid-of-your-project"
export FORMNEST_FORM_KEY="fm_a1b2c3d4e5f6"
```

---

## Submitting from a shell script

```bash
#!/usr/bin/env bash
# Send a deployment notification to a FormNest form

set -euo pipefail

FORM_KEY="${FORMNEST_FORM_KEY:-fm_a1b2c3d4e5f6}"
API_BASE="https://api.formnest.in"

curl -s -f -X POST "${API_BASE}/submit/${FORM_KEY}" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg env   "${ENVIRONMENT:-production}" \
    --arg sha   "${GITHUB_SHA:-$(git rev-parse HEAD)}" \
    --arg actor "${GITHUB_ACTOR:-$(whoami)}" \
    '{data: {environment: $env, commit_sha: $sha, deployed_by: $actor}}'
  )" \
  && echo "✅ Deployment notification sent" \
  || echo "⚠️  FormNest notification failed (non-fatal)"
```

---

## Listing submissions (curl)

```bash
# List the 20 most recent submissions
curl "https://api.formnest.in/api/v1/projects/${FORMNEST_PROJECT_ID}/forms/<form_id>/submissions" \
  -H "X-API-Key: ${FORMNEST_API_KEY}"

# Page 2, 50 per page
curl "https://api.formnest.in/api/v1/projects/${FORMNEST_PROJECT_ID}/forms/<form_id>/submissions?page=2&page_size=50" \
  -H "X-API-Key: ${FORMNEST_API_KEY}"

# Show spam submissions
curl "https://api.formnest.in/api/v1/projects/${FORMNEST_PROJECT_ID}/forms/<form_id>/submissions?is_spam=true" \
  -H "X-API-Key: ${FORMNEST_API_KEY}"
```

---

## Python

### Submit a form

```python
import os
import httpx

FORM_KEY = os.environ["FORMNEST_FORM_KEY"]
API_BASE = "https://api.formnest.in"

def submit_form(data: dict) -> str:
    """Submit data to a FormNest form. Returns the submission ID."""
    response = httpx.post(
        f"{API_BASE}/submit/{FORM_KEY}",
        json={"data": data},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["submission_id"]


# Example usage
submission_id = submit_form({
    "name": "Alice",
    "email": "alice@example.com",
    "message": "Hello from Python!",
})
print(f"Submitted: {submission_id}")
```

### Read submissions with pagination

```python
import os
import httpx
from typing import Iterator

API_BASE = "https://api.formnest.in"
API_KEY = os.environ["FORMNEST_API_KEY"]
PROJECT_ID = os.environ["FORMNEST_PROJECT_ID"]

def iter_submissions(form_id: str, page_size: int = 50) -> Iterator[dict]:
    """Yield all submissions for a form, handling pagination automatically."""
    client = httpx.Client(headers={"X-API-Key": API_KEY}, timeout=30)
    page = 1

    while True:
        r = client.get(
            f"{API_BASE}/api/v1/projects/{PROJECT_ID}/forms/{form_id}/submissions",
            params={"page": page, "page_size": page_size},
        )
        r.raise_for_status()
        body = r.json()

        for submission in body["submissions"]:
            yield submission

        if page * page_size >= body["total"]:
            break
        page += 1


# Export all submissions to CSV
import csv, sys

writer = csv.DictWriter(sys.stdout, fieldnames=[
    "id", "name", "email", "submitted_at", "spam_score"
])
writer.writeheader()

for sub in iter_submissions("your-form-id"):
    writer.writerow({
        "id": sub["id"],
        "name": sub.get("name", ""),
        "email": sub.get("email", ""),
        "submitted_at": sub["submitted_at"],
        "spam_score": sub["spam_score"],
    })
```

---

## Node.js / TypeScript

### Submit a form

```typescript
const FORM_KEY = process.env.FORMNEST_FORM_KEY!;
const API_BASE = "https://api.formnest.in";

async function submitForm(data: Record<string, unknown>): Promise<string> {
  const res = await fetch(`${API_BASE}/submit/${FORM_KEY}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ data }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(`FormNest error: ${error.detail}`);
  }

  const body = await res.json();
  return body.submission_id as string;
}

// Usage
const id = await submitForm({ name: "Alice", email: "alice@example.com" });
console.log("Submitted:", id);
```

### Read submissions

```typescript
const API_KEY = process.env.FORMNEST_API_KEY!;
const PROJECT_ID = process.env.FORMNEST_PROJECT_ID!;
const API_BASE = "https://api.formnest.in";

async function listSubmissions(formId: string, page = 1, pageSize = 20) {
  const url = new URL(
    `${API_BASE}/api/v1/projects/${PROJECT_ID}/forms/${formId}/submissions`
  );
  url.searchParams.set("page", String(page));
  url.searchParams.set("page_size", String(pageSize));

  const res = await fetch(url.toString(), {
    headers: { "X-API-Key": API_KEY },
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
```

---

## GitHub Actions — form submission on deploy

```yaml
# .github/workflows/notify.yml
name: Notify on Deploy

on:
  push:
    branches: [main]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Send deployment notification
        env:
          FORMNEST_FORM_KEY: ${{ secrets.FORMNEST_FORM_KEY }}
        run: |
          curl -s -X POST "https://api.formnest.in/submit/${FORMNEST_FORM_KEY}" \
            -H "Content-Type: application/json" \
            -d "{
              \"data\": {
                \"repository\": \"${{ github.repository }}\",
                \"branch\": \"${{ github.ref_name }}\",
                \"commit\": \"${{ github.sha }}\",
                \"actor\": \"${{ github.actor }}\",
                \"status\": \"deployed\"
              }
            }"
```

---

## API key rotation (automated)

```bash
#!/usr/bin/env bash
# Rotate the API key and update your secret manager

NEW_KEY=$(curl -s -X POST \
  "https://api.formnest.in/api/v1/projects/${FORMNEST_PROJECT_ID}/api-key/rotate" \
  -H "Authorization: Bearer ${FORMNEST_JWT}" \
  | jq -r '.api_key')

echo "New API key: ${NEW_KEY:0:10}…"

# Update in your secret manager, e.g. AWS Secrets Manager:
# aws secretsmanager put-secret-value \
#   --secret-id formnest/api-key \
#   --secret-string "$NEW_KEY"
```

---

## Error handling

All error responses follow the same JSON structure:

```json
{
  "error": "ERROR_CODE",
  "detail": "Human-readable message"
}
```

| Status | Code | Action |
|--------|------|--------|
| `401` | `UNAUTHORIZED` | Check your API key or token |
| `403` | `PLAN_LIMIT_EXCEEDED` | Upgrade your plan |
| `404` | `NOT_FOUND` | Check form_key / form_id |
| `410` | `FORM_NOT_ACTIVE` | Form is paused or deleted |
| `422` | `VALIDATION_ERROR` | Fix request body |
| `429` | `RATE_LIMIT_EXCEEDED` | Back off and retry |
| `503` | `SERVICE_UNAVAILABLE` | Retry with exponential backoff |

### Retry with backoff (Python)

```python
import time, httpx

def submit_with_retry(form_key: str, data: dict, max_retries: int = 3) -> dict:
    backoff = 1
    for attempt in range(max_retries):
        try:
            r = httpx.post(
                f"https://api.formnest.in/submit/{form_key}",
                json={"data": data},
                timeout=10,
            )
            if r.status_code == 429:
                time.sleep(backoff)
                backoff *= 2
                continue
            r.raise_for_status()
            return r.json()
        except httpx.TimeoutException:
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError("Max retries exceeded")
```
