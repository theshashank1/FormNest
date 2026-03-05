# 🏗️ FormNest — Architecture Documentation
**Manovratha Tech · Version 2.0 · Shashank**

> FormNest is a **serverless-experience SaaS** — developers embed one line of JavaScript and business owners collect structured, database-backed leads with zero backend knowledge. This document covers the complete system architecture, niche feature design decisions, and the planned merger bridge with TREEEX-WBSP.

---

## 📋 Table of Contents

1. [System Philosophy](#1-system-philosophy)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Core Components](#3-core-components)
4. [Niche Feature Architecture](#4-niche-feature-architecture)
5. [Data Flow Patterns](#5-data-flow-patterns)
6. [Technology Stack](#6-technology-stack)
7. [Serverless Infrastructure Design](#7-serverless-infrastructure-design)
8. [Security Architecture](#8-security-architecture)
9. [Scalability Considerations](#9-scalability-considerations)
10. [WBSP Merger Strategy](#10-wbsp-merger-strategy)
11. [Key Design Decisions (ADRs)](#11-key-design-decisions-adrs)
12. [Environment URLs](#12-environment-urls)

---

## 1. System Philosophy

### The Core Promise: "Build a Website With No Fear of Backend"

FormNest's central design principle is that **the end user — a developer building a client's website — should never need to provision a server, write API code, or manage a database** to capture structured lead data.

A developer embeds:
```html
<script src="https://cdn.formnest.in/widget.js" data-key="fm_abc123"></script>
```

And FormNest handles:
- Rendering a fully branded, accessible form on any website
- Auto-provisioning a typed PostgreSQL table for that form's submissions
- Spam protection (honeypot + rate limit + hCaptcha)
- Email notification to the project owner
- Outbound webhook to any connected tool (Slack, Notion, custom CRM)
- A clean dashboard for the business owner to review leads and export CSV

This is the **serverless experience layer** on top of real infrastructure. The developer gets simplicity; FormNest provides the durable backend.

### Architecture Pattern

FormNest is built as a **Modular Monolith with Distributed Workers** — the same pattern as TREEEX-WBSP — for deliberate future merger compatibility.

```
┌─────────────────────────────────────────────────────────────────┐
│                         FORMNEST                                │
├──────────────────┬───────────────────┬──────────────────────────┤
│  FORM ENGINE     │  BLOG + SEO CMS   │  DATA LAYER (CRM)        │
│                  │                   │                          │
│  JS Embed Widget │  Markdown Editor  │  Submissions Dashboard   │
│  Auto DB Tables  │  SEO Meta Engine  │  Lead Tagging            │
│  REST API        │  Dynamic Sitemap  │  CSV/Webhook Export      │
│  Spam Guard      │  Schema.org       │  Analytics               │
│  Multi-step Forms│  OG Image Gen     │  Lead Scoring (Phase 2)  │
│  Partial Save    │  Programmatic SEO │  WhatsApp Notify (P3)    │
└──────────────────┴───────────────────┴──────────────────────────┘
```

### Base URLs

| Environment | URL |
|---|---|
| **Local (Development)** | `http://localhost:8001` |
| **Production API** | `https://api.formnest.in` |
| **Dashboard** | `https://app.formnest.in` |
| **Widget CDN** | `https://cdn.formnest.in/widget.js` |
| **Public Blog** | `https://{slug}.formnest.in` or custom domain |
| **API Docs** | `https://api.formnest.in/docs` |

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL CLIENTS                              │
│                                                                          │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────────┐  │
│  │ JS Widget    │  │ React Dashboard  │  │ Next.js Public Blog       │  │
│  │ (any website)│  │ app.formnest.in  │  │ {slug}.formnest.in        │  │
│  └──────┬───────┘  └────────┬─────────┘  └──────────────┬────────────┘  │
│         │                   │                            │               │
└─────────┼───────────────────┼────────────────────────────┼───────────────┘
          │ HTTPS POST        │ HTTPS REST                 │ HTTPS GET
          │ (public)          │ (JWT auth)                 │ (public)
┌─────────▼───────────────────▼────────────────────────────▼───────────────┐
│                         APPLICATION LAYER                                │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI Server  (Port 8001)                   │    │
│  │  /api/v1/**  (authenticated)    /submit/**  (public, rate-limit) │    │
│  │  /blog/**   (public, cached)    /sitemap/** (public, cached)     │    │
│  └──────────────────────────────────┬───────────────────────────────┘    │
│                                     │ LPUSH                              │
│  ┌──────────────┐  ┌─────────────┐  │  ┌───────────────────────────┐     │
│  │  Submission  │  │  Email      │  │  │  Webhook Delivery         │     │
│  │  Worker      │  │  Worker     │  │  │  Worker                   │     │
│  └──────┬───────┘  └──────┬──────┘  │  └──────────────┬────────────┘     │
│         │                 │         │                  │                  │
│  ┌──────▼─────────────────▼─────────▼──────────────────▼────────────┐    │
│  │              Redis 7  (Queue + Cache + Rate Limiting)             │    │
│  └──────────────────────────────┬────────────────────────────────────┘    │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────────┐
│                            DATA LAYER                                    │
│                                                                          │
│  ┌─────────────────────┐   ┌──────────────────┐   ┌──────────────────┐  │
│  │  PostgreSQL 16       │   │  Cloudflare R2    │   │  Upstash Redis   │  │
│  │  (Neon.tech          │   │  (Media Storage)  │   │  (Serverless     │  │
│  │   Serverless)        │   │                  │   │   Queue/Cache)   │  │
│  └─────────────────────┘   └──────────────────┘   └──────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────────┐
│                         EXTERNAL SERVICES                                │
│                                                                          │
│  Supabase (Auth)     Razorpay (₹ billing)   Resend (email)              │
│  Stripe ($ Phase 2)  Cloudflare CDN          hCaptcha (spam)            │
│  WhatsApp API        TREEEX-WBSP Bridge      Sentry (errors)            │
│  (Phase 3 via WBSP)  (Phase 3)               Logfire (observability)    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 API Server (`server/api`)

**Framework:** FastAPI 0.110+ with async/await
**Port:** 8001
**Key Design:** Split between authenticated endpoints (`/api/v1`) and public endpoints (`/submit`, `/blog`, `/sitemap`) with different rate limiting and caching strategies.

**Endpoint Structure:**
```
/api/v1  (Bearer JWT required)
├── /auth                          # Signup, signin, OAuth, refresh, me
├── /projects                      # Project CRUD
│   └── /{project_id}
│       ├── /forms                 # Form schema management + DDL trigger
│       │   └── /{form_id}
│       │       ├── /submissions   # View, filter, tag, export
│       │       ├── /analytics     # Per-form stats
│       │       └── /preview       # Render form as HTML preview
│       ├── /blog                  # Blog CRUD + SEO meta
│       │   └── /{post_id}
│       │       └── /og-image      # OG image generation
│       ├── /tags                  # Tag management
│       ├── /webhooks              # Outbound webhook config
│       ├── /analytics             # Project-level aggregated stats
│       ├── /members               # Project member invites + RBAC
│       └── /settings              # Project config, notifications, branding
├── /billing                       # Razorpay subscription management
└── /account                       # User profile + notification prefs

/submit/{form_key}  (PUBLIC — rate limited per IP + form_key)
  └── POST           # Form submission (202 Accepted, async processing)

/f/{form_key}  (PUBLIC — server-side rendered form page)
  └── GET            # Standalone form page (for no-JS embed scenario)

/blog/{project_slug}/{post_slug}  (PUBLIC — cached at CDN)
  └── GET            # Blog post HTML

/sitemap/{project_slug}.xml  (PUBLIC — cached, regenerated on publish)
  └── GET            # Dynamic XML sitemap

/widget.js  (PUBLIC — cached at CDN, versioned)
  └── GET            # Vanilla JS embed script
```

### 3.2 Submission Worker (`server/workers/submission.py`)

**Purpose:** Process incoming form submissions asynchronously
**Queue:** `queue:submissions`
**Concurrency:** Async workers, horizontally scalable

**Processing Pipeline:**
```
POST /submit/{form_key}
         │
         ▼
API: Validate form_key → check rate limit → return 202 immediately
         │
         ▼ LPUSH queue:submissions
Redis Queue
         │
         ▼ BRPOP
Worker Pipeline:
  1. spam_check()      → honeypot, IP rate limit, pattern scoring
  2. validate_schema() → check required fields, types, max lengths
  3. enrich_meta()     → source URL, referrer, device type, UTM params
  4. db_insert()       → insert into dynamic table + index
  5. analytics_bump()  → increment submission_count, daily snapshot
  6. notify_email()    → LPUSH queue:emails (non-blocking)
  7. fire_webhooks()   → LPUSH queue:webhooks for each configured hook
  8. partial_cleanup() → delete any partial save session for this contact
```

### 3.3 Email Worker (`server/workers/email.py`)

**Purpose:** All transactional email via Resend.com
**Queue:** `queue:emails`

**Email Types:**
| Type | Trigger | Template |
|---|---|---|
| `new_submission` | Every form submission | `submission_alert.html` |
| `usage_warning_80` | 80% of plan limit reached | `usage_warning.html` |
| `usage_limit_reached` | 100% of plan limit | `limit_reached.html` |
| `welcome` | New signup | `welcome.html` |
| `subscription_activated` | First payment success | `subscription.html` |
| `weekly_digest` | Every Monday (Phase 2) | `digest.html` |

**Retry Logic:** 3 attempts — 30s, 2 min, 10 min exponential backoff. After max retries → `email_logs.status = failed`.

### 3.4 Webhook Delivery Worker (`server/workers/webhook.py`)

**Purpose:** Fire outbound webhooks to configured URLs on form events
**Queue:** `queue:webhooks`

**Payload (sent as `application/json`):**
```json
{
  "event": "form.submission",
  "form_id": "uuid",
  "form_name": "Contact Us",
  "project_id": "uuid",
  "submitted_at": "2025-06-01T10:30:00Z",
  "data": { "name": "Priya", "email": "priya@example.com", "message": "..." },
  "metadata": {
    "ip_hash": "sha256_hashed",
    "source_url": "https://client-site.com/contact",
    "utm_source": "google",
    "device": "mobile"
  }
}
```

**Security:** `X-FormNest-Signature: sha256=HMAC_HEX` header on every request. Receivers should validate this.

**Retry:** 3 attempts — 10s, 1 min, 5 min. Log all attempts to `webhook_delivery_logs`.

### 3.5 OG Image Worker (`server/workers/og_image.py`)

**Purpose:** Generate Open Graph images for blog posts on publish
**Queue:** `queue:og_images`
**Implementation:** Playwright headless browser renders an HTML template, exports PNG, uploads to Cloudflare R2, updates `blog_posts.og_image_url`.

---

## 4. Niche Feature Architecture

These are the **highest-leverage niche features** to build first — each solving a specific Indian developer/startup pain that competitors miss.

### 4.1 Multi-Step Form Engine

**Problem:** Single-page forms with 5+ fields have high abandonment rates. Surveys, onboarding forms, and qualification forms need progressive disclosure.

**Implementation:**
```
Form Schema JSONB → "steps" array → each step has fields + validation
Widget.js renders one step at a time → progress bar → previous/next
On final step → POST /submit/{form_key} with all accumulated step data
Partial progress → saved to Redis with TTL 24h (see 4.2)
```

**Schema Addition:**
```json
{
  "form_type": "multi_step",
  "steps": [
    { "step": 1, "title": "About You", "fields": ["name", "email"] },
    { "step": 2, "title": "Your Project", "fields": ["company", "budget"] },
    { "step": 3, "title": "Message", "fields": ["message", "timeline"] }
  ]
}
```

**Why Build First:** Every agency and startup with a qualification form (budget, project type) needs this. It directly increases lead quality and reduces junk submissions.

### 4.2 Partial Submission Saving (Ghost Leads)

**Problem:** Visitors start filling a form, abandon it halfway. That partial data is lost forever. Indian SMEs lose 60-80% of form starters before completion.

**Implementation:**
```
Widget.js debounce (1s after last keypress) → POST /submit/{key}/partial
  → Redis: SETEX partial:{form_key}:{fingerprint} 86400 {partial_json}
  → NOT inserted into PostgreSQL (to avoid fake data)

On return visit → GET /submit/{key}/partial?fp={fingerprint}
  → Restore pre-filled fields from Redis snapshot

On full submit → Redis key deleted + DB row inserted
On 24h TTL expiry → "ghost lead" archived to ghost_leads table (analytics only)
```

**Dashboard Impact:** "Ghost Leads" tab shows emails/phones captured from partial fills. Owner can manually follow up. This is a unique feature no Indian competitor offers.

### 4.3 Anti-Spam Stack (India-Optimised)

**Problem:** Indian websites receive disproportionately high bot spam. Standard CAPTCHA has poor UX. The result is that form data is polluted and useless.

**Layered Defence:**
```
Layer 1 — Honeypot Field
  Widget.js injects <input name="_gotcha" style="display:none">
  API: if data._gotcha is non-empty → mark as spam immediately

Layer 2 — IP Rate Limiting (Redis)
  Redis: INCR rate:{ip}:{form_key} EXPIRE 60
  > 5 submissions/minute from same IP → 429 + soft-block

Layer 3 — Timing Check
  Widget.js stamps submit_started_at on form load
  API: if (submitted_at - started_at) < 2s → spam score +40

Layer 4 — Content Pattern Scoring
  Check for: URL density, repeated characters, known spam phrases
  Spam score threshold: > 70 → flag as spam (not inserted into main table)

Layer 5 — hCaptcha (Optional, project-level toggle)
  For high-spam projects: embed hCaptcha in widget
  API: verify token with hCaptcha secret before processing
  hCaptcha chosen over reCAPTCHA → no Google dependency, GDPR friendly
```

**Why Build First:** The #1 complaint from Indian developers using Google Forms or Formspree is spam. A clean inbox is the core value proposition.

### 4.4 Programmatic SEO Support

**Problem:** Indian agencies build landing pages for every city/service combination (e.g. "Plumber in Bangalore", "Plumber in Pune"). Each page needs a unique blog/landing page. Doing this manually is impossible.

**Implementation:**
```
Template Engine: Blog post with {{variables}} → template_post record
  e.g. "Best {{service}} in {{city}} — Complete Guide 2025"

Data Source: project owner uploads CSV: city, service, local_keyword
  → stored in programmatic_seo_datasets table

Generation Worker: 
  For each row in dataset → render template → create blog_post record
  Auto-generates: slug, title, meta_description, schema_markup
  Rate: 100 pages/minute (worker throttle to avoid Neon write saturation)

Sitemap: auto-includes all generated pages

Use Case: Agency creates one template, uploads 500 city rows → 500 SEO pages
```

**Why Build First:** Digital agencies in India are desperate for programmatic SEO tooling at Indian prices. Tools like SEOmatic cost $500+/month. This can be a standalone upsell.

### 4.5 Native Notion & Google Sheets Sync

**Problem:** Every Indian startup owner keeps their leads in Google Sheets or Notion. They don't want a new dashboard — they want data in the tool they already use.

**Implementation:**
```
OAuth connect flow:
  /api/v1/projects/{id}/integrations/notion/connect
  /api/v1/projects/{id}/integrations/gsheets/connect

Submission Worker adds step:
  if project.notion_sync_enabled → POST to Notion API (append row to DB)
  if project.gsheets_sync_enabled → POST to Sheets API (append row)

Mapping config (stored in project_integrations table):
  form field → Notion property name
  form field → Sheet column letter
```

**Why Build First:** "Just push my leads to my Notion database" is the most-requested feature in Indian indie developer communities. This alone can drive word-of-mouth.

### 4.6 UTM + Source Analytics

**Problem:** Business owners want to know which marketing channel their leads came from. No Indian form tool provides this out of the box.

**Implementation:**
```
Widget.js captures on load:
  utm_source, utm_medium, utm_campaign, utm_content, utm_term
  document.referrer → normalised source (google, direct, facebook, etc.)
  screen width category → mobile/tablet/desktop

Stored in form_submission_index.utm_data (JSONB) and submission_analytics table

Dashboard shows:
  "Top lead sources this month: Google Organic (42%), WhatsApp link (28%), Direct (18%)"
  "Mobile vs Desktop split: 73% mobile"
  "Peak submission time: 8PM - 10PM IST"
```

**Why Build First:** This is zero-infrastructure cost (client-side data collection) and delivers massive perceived value to business owners. Makes FormNest feel like a proper analytics tool.

### 4.7 Form Version Control & A/B Testing

**Problem:** When a developer edits a form schema, old submissions become inconsistent with new fields. There's no safe way to change a live form.

**Implementation:**
```
Every schema change → increment forms.schema_version
Old schema version stored in form_schema_versions table (JSONB snapshot)

Submissions tagged with schema_version_id at insert time
Dashboard can filter by version → "Submissions from v1 form" vs "v2 form"

A/B Test mode (Phase 2):
  Two schema variants (A/B) → Widget randomly assigns visitor to variant
  Submission tagged with variant → dashboard shows conversion by variant
```

**Why Build First:** This prevents the most common developer support ticket: "I changed my form and now old submissions look broken." Form versioning is a niche developer trust feature.

### 4.8 Standalone Form Pages (No-JS Embed Fallback)

**Problem:** Some platforms (certain email clients, AMP pages, old CMS installs) block or don't render JavaScript. Developers lose the form entirely.

**Implementation:**
```
GET /f/{form_key}
  → Server-side rendered full HTML form page
  → CSS-inlined, zero JS required
  → Submits via standard HTML form POST to /submit/{form_key}
  → Hosted at formnest.in/f/{key} — developer can iframe or link to it

Use Case: "Embed this form in your email newsletter"
  → Link: https://formnest.in/f/fm_abc123
  → Works in any email client
```

---

## 5. Data Flow Patterns

### 5.1 Form Submission Flow (Primary)

```
Visitor fills form on client-site.com
         │
         ▼
Widget.js:
  - Collect UTM params, referrer, device
  - Check partial_save session (restore if exists)
  - On submit: validate client-side → show loading state
         │
         ▼ POST /submit/{form_key}
         │ {fields + metadata + spam_signals}
         │
FastAPI:
  - Lookup form by form_key (Redis cache, 5min TTL)
  - Check IP rate limit (Redis INCR)
  - Return 202 Accepted immediately
  - LPUSH queue:submissions
         │
         ▼
Redis Queue: queue:submissions
         │
         ▼ BRPOP
Submission Worker:
  1. spam_check()
  │
  ├──(spam)──▶ INSERT submissions spam=TRUE, notify owner
  │
  └──(clean)─▶ INSERT into proj_{id}_form_{id} table
               INSERT into form_submission_index
               LPUSH queue:emails
               LPUSH queue:webhooks (per configured hook)
               INCR analytics counters
         │
         ▼
Dashboard update:
  - SSE or polling /api/v1/projects/{id}/forms/{id}/submissions?since=...
  - New submission appears with all metadata
```

### 5.2 Blog Post Publish Flow

```
Owner writes Markdown in Dashboard editor
         │
         ▼
Save draft → auto-save every 30s (no queue, direct DB write)
         │
         ▼
Publish button → POST /api/v1/projects/{id}/blog/{post_id}/publish
         │
FastAPI:
  - Validate: title, content length, slug uniqueness
  - Set status = published, published_at = now()
  - LPUSH queue:og_images (async OG image generation)
  - Invalidate CDN cache for /blog/{project_slug}/{post_slug}
  - Regenerate sitemap (async via queue:sitemaps)
         │
         ▼
Public URL immediately live:
  GET https://{slug}.formnest.in/{post_slug}
  → Next.js fetches from API → SSR → served via Cloudflare CDN
```

### 5.3 Webhook Delivery Flow

```
Submission Worker publishes to queue:webhooks:
  {hook_id, submission_id, payload}
         │
         ▼
Webhook Worker:
  1. Load hook config (url, secret, events, headers)
  2. Build payload + HMAC signature
  3. POST to target URL (5s timeout)
         │
         ├── 2xx response → log success → done
         │
         ├── Timeout / 5xx → backoff retry (10s, 1min, 5min)
         │
         └── 4xx → log permanent failure (not retried — owner must fix URL)
         │
         ▼
All attempts logged to webhook_delivery_logs (status, duration, response_code)
Dashboard shows delivery history per hook
```

---

## 6. Technology Stack

### Application

| Component | Technology | Version | Rationale |
|---|---|---|---|
| **Runtime** | Python | 3.12+ | Async-native, shared with WBSP |
| **Framework** | FastAPI | 0.110+ | Same as WBSP — merger ready |
| **ASGI Server** | Uvicorn | Latest | Production-grade, same as WBSP |
| **Validation** | Pydantic v2 | 2.x | Same as WBSP |
| **ORM** | SQLAlchemy | 2.0 async | Same as WBSP |
| **Queue** | Redis + ARQ | Latest | ARQ = async-native alternative to Celery |
| **Widget** | Vanilla JS ES2020 | N/A | Zero deps, Shadow DOM, works everywhere |

### Data

| Component | Technology | Provider | Rationale |
|---|---|---|---|
| **Database** | PostgreSQL 16 | Neon.tech | Serverless Postgres — scales to zero, branching |
| **Cache/Queue** | Redis 7 | Upstash | Serverless Redis — pay-per-request |
| **Media** | Object Storage | Cloudflare R2 | Zero egress fees — Indian users benefit hugely |
| **CDN** | Cloudflare | Free/Pro | Widget.js + blog pages cached globally |

### Frontend

| Component | Technology | Rationale |
|---|---|---|
| **Dashboard** | React + Vite + Tailwind | Fast dev, SPA |
| **Public Blog** | Next.js 14 (App Router) | SSR + ISR for SEO |
| **Widget** | Vanilla JS | No framework deps |
| **UI Components** | shadcn/ui | Consistent, accessible |

### Infrastructure

| Component | Technology | Rationale |
|---|---|---|
| **API Hosting** | Railway or Render | Cheap, simple, India-proximate |
| **DB** | Neon.tech | Serverless Postgres, $0 at idle |
| **Redis** | Upstash | Serverless Redis, $0 at idle |
| **Media** | Cloudflare R2 | No egress fees |
| **Auth** | Supabase | Shared with WBSP — same project |
| **Email** | Resend.com | Developer-friendly, reliable |
| **Payments** | Razorpay (₹) + Stripe ($) | INR-native billing |
| **Errors** | Sentry | Free tier sufficient at MVP |

### Why Neon.tech for Database (Not Supabase DB or RDS)

Neon.tech provides **database branching** — every GitHub PR gets its own database branch that is a copy-on-write clone of production. This makes migrations zero-risk. It also scales to zero when idle, keeping costs under ₹500/month at MVP stage.

---

## 7. Serverless Infrastructure Design

FormNest is designed to run at near-zero cost when idle and scale automatically under load. This is critical for a bootstrapped Indian product.

### Cost at Zero Traffic (Monthly Estimate)

| Service | Plan | Cost |
|---|---|---|
| Neon.tech PostgreSQL | Free tier | ₹0 |
| Upstash Redis | Free tier | ₹0 |
| Cloudflare R2 | 10GB free | ₹0 |
| Cloudflare CDN | Free | ₹0 |
| Railway API hosting | Hobby | ~₹400 |
| Supabase Auth | Free tier | ₹0 |
| Resend Email | Free (3k/month) | ₹0 |
| **Total** | | **~₹400/month** |

**Break-even:** 1 Starter plan subscriber (₹449/month) covers all infrastructure costs.

### Scaling Path

```
Stage 1 — MVP (₹0–₹50K MRR)
  Railway Hobby → Neon Free → Upstash Free → Cloudflare Free
  Estimated infra: ₹400–₹2,000/month

Stage 2 — Growth (₹50K–₹3L MRR)
  Railway Pro (autoscale) → Neon Scale → Upstash Pay-as-you-go
  Estimated infra: ₹5,000–₹20,000/month

Stage 3 — Scale (₹3L+ MRR)
  Azure Container Apps (same as WBSP) → Neon Business → dedicated Redis
  Merger readiness: both products on same infra
  Estimated infra: ₹30,000–₹80,000/month
```

---

## 8. Security Architecture

### Authentication Flow

```
User signup/signin → Supabase Auth → JWT (access_token + refresh_token)
                          │
                          ▼
FastAPI middleware → verify JWT with Supabase JWKS endpoint
  → extract user_id (sub claim)
  → load project membership from DB (cached in Redis 5 min)
  → attach to request context
```

### Public Endpoint Security

```
POST /submit/{form_key}:
  - Rate limit: 5 requests/minute per IP per form_key (Redis sliding window)
  - No auth required (it's a public form)
  - form_key is the only secret — if leaked, owner can regenerate
  - All submission data sanitised (strip HTML, truncate to field max)

GET /blog/** and /sitemap/**:
  - Fully public, cached at Cloudflare edge
  - No rate limiting (CDN handles it)
  - Project owner controls content (no user-generated risk)
```

### Data Security Layers

1. **Transport:** HTTPS everywhere. TLS 1.3. HSTS headers.
2. **Auth:** Supabase JWT. Short expiry (1h). Refresh tokens for renewal.
3. **RBAC:** Project-level roles. Only `OWNER` and `ADMIN` can configure webhooks/billing.
4. **PII:** Email and phone in submissions encrypted at column level (AES-256).
5. **Webhook Secrets:** HMAC-SHA256 signed payloads. Secret stored hashed, never returned in API.
6. **API Keys:** `fm_` prefixed, regeneratable, scoped to project.

---

## 9. Scalability Considerations

### The Dynamic Table Problem

Each form creates a PostgreSQL table. At scale (10K forms), PostgreSQL handles this fine — the limit is typically 1 billion relations. However, `pg_catalog` queries can slow down with many tables.

**Mitigation:**
- Table naming convention: `fn_proj_{short_id}_form_{short_id}` (deterministic, queryable)
- All submissions also indexed in `form_submission_index` — dashboard queries hit this table, not N dynamic tables
- Maintenance: `FormTableMigrationService` handles `ALTER TABLE` for schema changes
- Connection pooling: PgBouncer (or Neon's built-in pooling) to avoid per-table connection overhead

### Performance Targets (MVP → Scale)

| Metric | MVP Target | Scale Target |
|---|---|---|
| POST /submit response | < 300ms | < 150ms |
| Dashboard page load | < 1.5s | < 800ms |
| Widget.js size | < 12KB gzipped | < 10KB |
| Widget load time | < 400ms | < 200ms (CDN) |
| Submission processing | < 3s end-to-end | < 1s |

---

## 10. WBSP Merger Strategy

### Vision

When FormNest reaches ₹50K+ MRR (Year 1–2), a **phased bridge integration** with TREEEX-WBSP creates a unified "Growth Infrastructure Platform":

```
Form collects lead → WhatsApp campaign nurtures → CRM tracks lifecycle
Everything under one subscription, one dashboard, one billing
```

### Why Merger is Architecturally Easy

FormNest is intentionally designed with WBSP schema patterns in mind:

| FormNest Concept | WBSP Equivalent | Merger Action |
|---|---|---|
| `projects` | `workspaces` | Add `wbsp_workspace_id` FK — already stubbed |
| `form_submission_index` | `contacts` | BridgeService syncs email/phone to WBSP contacts |
| `tags` | `tags` | Identical schema — shared tag service |
| `project_members` | `workspace_members` | Identical RBAC — direct merge |
| Supabase auth | Supabase auth | **Already shared** — same project |
| Redis queues | Redis queues | **Same infra** — separate queue keys |
| FastAPI + SQLAlchemy | FastAPI + SQLAlchemy | **Same framework stack** |

### Three-Phase Merger Plan

**Phase A — Bridge Layer (Month 12–18)**
```
FormNest Submission Worker
  → BridgeService.sync_contact(submission)
    → POST /api/v1/workspaces/{wbsp_id}/contacts  (WBSP internal API)
      → if contact exists (by phone/email) → PATCH (merge fields)
      → if new → CREATE with tag "formnest_lead"
    → Store wbsp_contact_id in form_submission_index
  → New dashboard tab: "WhatsApp this lead" button (opens WBSP conversation)
```

**Phase B — Unified Workspace (Month 18–24)**
```
User creates one Workspace
  → Form Builder tab (FormNest engine)
  → WhatsApp tab (WBSP channels + templates)
  → CRM tab (unified contacts from both)
  → Billing: one subscription covers both modules
```

**Phase C — Full Growth Platform (Year 2+)**
```
Lead capture → Instant WhatsApp → Automated campaign → Conversion tracking
Programmatic SEO → Blog → Form → WhatsApp → Close
```

### Schema Pre-Alignment (Already in FormNest from Day 1)

```sql
-- On projects table (nullable, unused until merger)
wbsp_workspace_id  UUID NULL
wbsp_sync_enabled  BOOLEAN DEFAULT FALSE

-- On form_submission_index (nullable, populated by BridgeService)
wbsp_contact_id   UUID NULL
wbsp_synced_at    TIMESTAMPTZ NULL
```

---

## 11. Key Design Decisions (ADRs)

### ADR-001: Dynamic DDL for Auto Table Creation

**Context:** Core innovation — auto-create a PostgreSQL table per form.

**Decision:** Use SQLAlchemy `text()` with parameterised DDL. Tables: `fn_proj_{short_id}_form_{short_id}`. Executed once when form is first activated.

**Consequences:**
- ✅ Real typed columns — each form's data is independently queryable
- ✅ CSV export is a simple `SELECT *` on a well-structured table
- ⚠️ Alembic cannot track — managed by `FormTableMigrationService`
- ⚠️ Schema changes to live forms require `ALTER TABLE` (handled by migration service)

---

### ADR-002: Submission Index Table as Bridge

**Context:** N dynamic tables make cross-form dashboard queries expensive.

**Decision:** `form_submission_index` is a lightweight materialized index — stores submission ID, form ID, project ID, timestamp, and a JSONB snapshot of the first 5 fields. Full data lives in dynamic table.

**Merger Benefit:** WBSP bridge reads this table to sync contacts without touching dynamic tables.

---

### ADR-003: Shared Supabase Auth Project with WBSP

**Decision:** Both FormNest and WBSP use the **same Supabase project** for auth.

**Consequences:**
- ✅ Single sign-on between products from day one
- ✅ Same user UUIDs — no migration at merger time
- ⚠️ Outage on Supabase affects both products

---

### ADR-004: ARQ over Celery for Task Queue

**Context:** WBSP uses a custom Redis-based queue. For FormNest, a proper task queue library is needed.

**Decision:** Use **ARQ** (Async Redis Queue) — a lightweight Python library that runs async coroutines as background tasks via Redis. No Celery/RabbitMQ complexity.

**Consequences:**
- ✅ Fully async — integrates natively with FastAPI's async stack
- ✅ Same Redis instance used for rate limiting, caching, and queuing
- ✅ Simpler than Celery — no separate broker config, no pickle serialisation
- ⚠️ Less mature than Celery — fewer third-party integrations

---

### ADR-005: Neon.tech over Supabase DB or AWS RDS

**Decision:** Use Neon.tech for PostgreSQL hosting.

**Consequences:**
- ✅ Database branching — PR-level database previews, zero-risk migrations
- ✅ Scales to zero when idle — ₹0 infra cost at launch
- ✅ Compatible with asyncpg driver used by WBSP (merger-ready)
- ⚠️ Not as battle-tested as RDS at extreme scale — migrate at ₹5L+ MRR

---

### ADR-006: Vanilla JS Widget in Shadow DOM

**Decision:** `widget.js` is vanilla ES2020 with zero dependencies. Renders into Shadow DOM.

**Consequences:**
- ✅ Works on WordPress, Wix, plain HTML, React, Vue, Angular without conflicts
- ✅ Isolated CSS — host site styles don't bleed into form
- ✅ Can be open-sourced on GitHub (trust builder with developers)
- ⚠️ No React component library — UI hand-crafted
- ⚠️ Shadow DOM has limited Firefox private browsing quirks (acceptable)

---

### ADR-007: PostgreSQL FTS for Blog Search

**Decision:** Use PostgreSQL GIN index on `tsvector` for blog post search. No external search service.

**Consequences:**
- ✅ Zero additional cost — runs in same DB
- ✅ Sufficient for < 10,000 posts per project
- ⚠️ Migrate to Typesense/Meilisearch at scale (> 100K posts workspace-wide)

---

## 12. Environment URLs

| Service | Development | Production |
|---|---|---|
| API Server | `http://localhost:8001` | `https://api.formnest.in` |
| Dashboard | `http://localhost:5173` | `https://app.formnest.in` |
| Public Blog | `http://localhost:3000` | `https://{slug}.formnest.in` |
| Standalone Form | `http://localhost:8001/f/{key}` | `https://formnest.in/f/{key}` |
| Widget CDN | `http://localhost:8001/widget.js` | `https://cdn.formnest.in/widget.js` |
| API Docs | `http://localhost:8001/docs` | `https://api.formnest.in/docs` |
| Redis | `localhost:6379` | Upstash Redis URL |
| PostgreSQL | `localhost:5432/formnest_dev` | Neon.tech connection string |

---

## 📚 Related Documentation

- **[Database Schema](DATABASE_SCHEMA.md)** — Detailed table structures and relationships
- **[Project Roadmap](PROJECT_ROADMAP.md)** — Phased development plan
- **[WBSP Architecture](../wbsp/docs/architecture/ARCHITECTURE.md)** — TREEEX-WBSP system design (merger target)
- **[API Reference](../api/README.md)** — Complete endpoint docs (FastAPI auto-generated)

---

*FormNest Architecture v2.0 · Manovratha Tech · Shashank*
*Designed for merger compatibility with TREEEX-WBSP · Target merger: Year 1–2*
