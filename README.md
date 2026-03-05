# FormNest

Serverless-experience SaaS — embed forms, collect leads, zero backend knowledge required.

---

## Getting Started (Local Development)

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL 15+ (local or managed, e.g. Neon.tech)
- Redis (local or managed, e.g. Upstash) — optional for development

### 1. Install dependencies

```bash
pip install uv          # one-time install if uv is not on your PATH
uv sync                 # installs all project dependencies into .venv
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your values:
#   DATABASE_URL  — PostgreSQL connection string
#   SUPABASE_URL / SUPABASE_KEY — from your Supabase project dashboard
#   REDIS_URL     — Redis connection string (optional for local dev)
```

**Local PostgreSQL** (no SSL needed):
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/formnest_dev
DB_REQUIRE_SSL=false
```

**Managed cloud DB** (Neon, Supabase, Azure — SSL required):
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
DB_REQUIRE_SSL=true
```

### 3. Apply database migrations

```bash
uv run alembic upgrade head
```

This creates all tables. Re-run after pulling new changes that include new migration files.

### 4. Start the development server

```bash
uv run python run.py
```

The API is now available at <http://localhost:8001>.
Interactive docs: <http://localhost:8001/docs>

### 5. Start background workers (optional)

In a separate terminal:

```bash
uv run python run_workers.py
```

---

## Docker (Production-like)

```bash
cp .env.example .env   # fill in production values
docker compose up --build
```

Run migrations before the first start:

```bash
docker compose run --rm api uv run alembic upgrade head
```

---

## Key API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/signup` | — | Register a new user |
| `POST` | `/api/v1/auth/signin` | — | Sign in, get JWT |
| `POST` | `/api/v1/projects` | JWT | Create a project |
| `GET`  | `/api/v1/projects` | JWT | List your projects |
| `POST` | `/api/v1/projects/{id}/forms` | JWT | Create a form |
| `GET`  | `/api/v1/projects/{id}/forms` | JWT | List forms |
| `GET`  | `/f/{form_key}` | — | Public form schema |
| `POST` | `/submit/{form_key}` | — | Submit a form response |
| `GET`  | `/embed/{form_key}` | — | Embed snippets (iframe/JS/React/curl) |
| `GET`  | `/embed/{form_key}/iframe` | — | Standalone iframe HTML |
| `GET`  | `/api/v1/projects/{pid}/forms/{fid}/submissions` | JWT | List submissions |
| `GET`  | `/api/v1/projects/{pid}/forms/{fid}/submissions/{sid}` | JWT | Submission detail |
| `GET`  | `/health` | — | Health check |
| `GET`  | `/ready` | — | Readiness check (DB + Redis) |

### Submitting via curl (CLI)

```bash
# Get the form key from your dashboard or GET /api/v1/projects/{id}/forms
curl -X POST https://your-api/submit/<form_key> \
  -H "Content-Type: application/json" \
  -d '{"data": {"email": "user@example.com", "name": "Alice"}}'
```

### Embedding in HTML

```html
<iframe
  src="https://your-api/embed/<form_key>/iframe"
  width="100%" height="600" frameborder="0"
></iframe>
```

### Embedding in React

```jsx
// Get the snippet from GET /embed/<form_key>
import { FormNest } from '@formnest/react';

export default function MyPage() {
  return (
    <FormNest
      formKey="<form_key>"
      onSuccess={(id) => console.log('Submitted:', id)}
    />
  );
}
```

---

## Project Structure

```
server/
  api/          FastAPI routers (auth, projects, forms, submissions, public)
  core/         Config, DB engine, Redis, Supabase client, monitoring
  models/       SQLAlchemy ORM models
  schemas/      Pydantic request/response schemas
  services/     Business logic (submissions, dynamic tables)
  workers/      Background job processors
alembic/
  versions/     Migration files — run `alembic upgrade head` to apply
```
