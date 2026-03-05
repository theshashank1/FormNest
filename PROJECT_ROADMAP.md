# 🗺️ FormNest — Project Roadmap
**Manovratha Tech · Version 1.0 · Shashank**

> Phased development plan from zero to WBSP merger. Each phase has a clear "done" definition, revenue milestone, and go/no-go decision gate before the next phase begins.

---

## 📋 Table of Contents

1. [Overview & Philosophy](#1-overview--philosophy)
2. [Phase 0 — Foundation](#2-phase-0--foundation-weeks-14)
3. [Phase 1 — MVP Launch](#3-phase-1--mvp-launch-weeks-512)
4. [Phase 2 — Growth Features](#4-phase-2--growth-features-months-46)
5. [Phase 3 — Scale & Monetise](#5-phase-3--scale--monetise-months-79)
6. [Phase 4 — WBSP Bridge](#6-phase-4--wbsp-bridge-months-1018)
7. [Phase 5 — Unified Platform](#7-phase-5--unified-platform-months-1824)
8. [Milestone Summary](#8-milestone-summary)
9. [Feature Backlog](#9-feature-backlog)

---

## 1. Overview & Philosophy

### Build Order Principle

> **Build the smallest thing that creates a complete loop: embed → submit → see leads.**

Every phase extends this loop. Don't build analytics before you have submissions. Don't build the blog before you have paying customers. Don't build WBSP integration before you have leads worth nurturing.

### Revenue-Gated Phases

| Phase | Revenue Gate | Decision |
|---|---|---|
| 0 → 1 | — | Internal go/no-go |
| 1 → 2 | First paying customer | Real validation |
| 2 → 3 | ₹10K MRR | Product-market fit signal |
| 3 → 4 | ₹30K MRR | Scale is justified |
| 4 → 5 | ₹50K MRR | Merger economics work |

### Constraints

- Solo founder (Shashank) for Phase 0–2, possibly 1 hire at Phase 3
- Infrastructure must cost < ₹2,000/month until ₹20K MRR
- All tech decisions must be merger-compatible with TREEEX-WBSP

---

## 2. Phase 0 — Foundation (Weeks 1–4)

**Goal:** Working local dev environment. DB schema deployed. Basic auth. Can create a form and see it render.

### Deliverables

#### Infrastructure Setup
- [ ] Railway project created (API + worker services)
- [ ] Neon.tech database provisioned (`formnest_dev`, `formnest_prod`)
- [ ] Upstash Redis instance created
- [ ] Cloudflare R2 bucket created (`formnest-media`)
- [ ] Supabase project created (shared with WBSP — same project, new schema prefix)
- [ ] Cloudflare zone configured (`formnest.in`, `api.formnest.in`, `app.formnest.in`)

#### Repository Structure
```
formnest/
├── server/
│   ├── api/          # FastAPI app
│   ├── workers/      # ARQ background workers
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── tasks/        # Scheduled jobs (retention, cleanup)
├── widget/           # Vanilla JS embed widget
├── dashboard/        # React + Vite + Tailwind
├── blog/             # Next.js public blog
└── docs/             # ARCHITECTURE.md, DATABASE_SCHEMA.md, this file
```

#### Database
- [ ] All static tables migrated via Alembic (`users`, `projects`, `forms`, `form_submission_index`, etc.)
- [ ] `FormTableMigrationService` implemented (DDL for dynamic tables)
- [ ] Seed script for local dev data

#### Auth
- [ ] Supabase Auth signup/signin working
- [ ] JWT middleware on FastAPI
- [ ] Project membership check middleware

#### Core API (Skeleton)
- [ ] `POST /api/v1/projects` — create project
- [ ] `POST /api/v1/projects/{id}/forms` — create form (triggers DDL)
- [ ] `GET /api/v1/projects/{id}/forms/{id}` — fetch form schema
- [ ] `POST /submit/{form_key}` — accept submission (synchronous for now, queue in Phase 1)

#### Widget v0
- [ ] Vanilla JS renders form from schema JSON
- [ ] Submits to `/submit/{form_key}`
- [ ] Success/error state display
- [ ] Shadow DOM isolation

### ✅ Phase 0 Done When
- Developer can embed `<script data-key="fm_xxx">` on a plain HTML page
- Fill and submit a form
- See the submission appear in the database
- No bugs in the core loop

---

## 3. Phase 1 — MVP Launch (Weeks 5–12)

**Goal:** Public launch. First paying customer. Real form submissions from real users.

### Core Features

#### Async Submission Pipeline
- [ ] Redis queue (`queue:submissions`) — API returns 202 immediately
- [ ] Submission Worker: spam check → validate → DB insert → analytics bump
- [ ] Honeypot field in widget (Layer 1 spam)
- [ ] IP rate limiting via Redis (Layer 2 spam)
- [ ] Timing check (Layer 3 spam)

#### Email Notifications
- [ ] Email Worker (`queue:emails`)
- [ ] Resend.com integration
- [ ] `new_submission` email with formatted field data
- [ ] `usage_warning_80` and `usage_limit_reached` emails

#### Dashboard MVP
- [ ] Auth flow (signup, signin, forgot password)
- [ ] Project creation wizard
- [ ] Form builder — drag-drop fields, set required/optional
- [ ] Submissions list — paginated, searchable
- [ ] Basic stats: total submissions, today's count
- [ ] CSV export

#### Billing
- [ ] Razorpay subscription integration
- [ ] Starter (₹449/mo), Growth (₹999/mo), Agency (₹1,999/mo) plans
- [ ] Plan limits enforced in submission worker (soft block at 100%)
- [ ] Billing dashboard tab (current plan, usage, upgrade CTA)

#### Widget v1
- [ ] UTM param capture on form load
- [ ] Referrer + device detection
- [ ] hCaptcha integration (optional toggle per form, Layer 5 spam)
- [ ] Styled default theme (clean, works on any background)
- [ ] Custom branding: `primary_color`, `button_text`, `border_radius`

#### Standalone Form Pages
- [ ] `GET /f/{form_key}` — SSR form page, CSS-inlined, zero JS required
- [ ] Works as iframe embed for email newsletters

#### Webhooks (Basic)
- [ ] Webhook CRUD in dashboard
- [ ] Webhook Delivery Worker (`queue:webhooks`)
- [ ] HMAC-SHA256 signed payloads
- [ ] Delivery log visible in dashboard

### Launch Checklist
- [ ] Privacy Policy + Terms of Service pages
- [ ] DPDP Act consent checkbox in widget (configurable)
- [ ] `help.formnest.in` or basic docs site
- [ ] Sentry error monitoring connected
- [ ] Uptime monitoring (Better Uptime or similar)
- [ ] Product Hunt / IndieHackers launch post drafted

### ✅ Phase 1 Done When
- Public at `app.formnest.in`
- First customer pays ₹449
- 3 developers have embedded the widget on real client sites
- Zero critical bugs open

---

## 4. Phase 2 — Growth Features (Months 4–6)

**Revenue Gate:** ₹10K MRR before starting Phase 3

**Goal:** Ship the niche features that drive word-of-mouth in Indian dev communities.

### Multi-Step Forms
- [ ] `form_type: multi_step` support in form builder
- [ ] Widget renders step-by-step with progress bar
- [ ] Previous / Next navigation
- [ ] Client-side validation per step before advancing
- [ ] Final step submits all accumulated data

### Ghost Leads (Partial Submission Saving)
- [ ] `POST /submit/{key}/partial` endpoint (Redis SETEX 24h)
- [ ] Widget debounce (1s) sends partial data on each keystroke
- [ ] `GET /submit/{key}/partial?fp={fingerprint}` restores pre-filled fields on return
- [ ] `ghost_leads` table archival on TTL expiry
- [ ] "Ghost Leads" tab in dashboard: shows emails/phones captured from abandons
- [ ] Ghost lead → submission conversion tracking

### Native Notion Sync
- [ ] OAuth connect flow for Notion
- [ ] Notion database selector in integration settings
- [ ] Field-to-property mapping UI
- [ ] Submission Worker step: sync to Notion on each submit
- [ ] Error handling + retry on Notion API failure

### Native Google Sheets Sync
- [ ] OAuth connect flow for Google Sheets
- [ ] Sheet selector + column mapping UI
- [ ] Submission Worker step: append row to sheet
- [ ] Auto-create header row on first submission

### UTM + Source Analytics Dashboard
- [ ] Analytics page: submissions over time (7d, 30d, 90d)
- [ ] Top sources chart (Google, Direct, WhatsApp, Facebook, etc.)
- [ ] Device split (mobile / desktop / tablet)
- [ ] UTM breakdown (campaign, medium, source)
- [ ] Peak submission hours heatmap

### Form Version Control
- [ ] `form_schema_versions` table populated on every schema change
- [ ] Dashboard shows version history with diff view
- [ ] Submissions tagged with `schema_version_id`
- [ ] Filter submissions by version in dashboard

### Content-Pattern Spam Scoring (Layer 4)
- [ ] URL density scorer
- [ ] Repeated character detector
- [ ] Known spam phrase list (Indian English patterns)
- [ ] Spam score threshold: > 70 → flag (not reject — dashboard shows flagged)

### Blog CMS (Phase 2 Basic)
- [ ] Markdown editor in dashboard (CodeMirror or similar)
- [ ] Blog post CRUD: create, edit, publish, archive
- [ ] Public URL: `{project_slug}.formnest.in/{post_slug}`
- [ ] SEO meta fields: title, description, OG image upload
- [ ] Dynamic XML sitemap regenerated on publish
- [ ] PostgreSQL FTS search on `search_vector`

### ✅ Phase 2 Done When
- ₹10K MRR
- Multi-step forms live in production with at least 3 customers using them
- Ghost leads feature shipping — can demonstrate recovered leads to customers
- Notion or Sheets sync working for at least 5 projects

---

## 5. Phase 3 — Scale & Monetise (Months 7–9)

**Revenue Gate:** ₹30K MRR before starting Phase 4

**Goal:** Increase revenue per customer. Expand to agency/enterprise market. Harden infrastructure.

### Programmatic SEO Engine
- [ ] Template engine with `{{variable}}` placeholders
- [ ] CSV upload UI for dataset rows
- [ ] PSeo generation worker (100 pages/minute throttle)
- [ ] Generated pages appear in sitemap automatically
- [ ] Dashboard: progress indicator, success/failure per row
- [ ] Agency use case: "Plumber in {{city}}" × 500 cities

### OG Image Auto-Generation
- [ ] OG Image Worker (Playwright headless)
- [ ] Default template: title + project logo + background
- [ ] Generated PNG uploaded to Cloudflare R2
- [ ] `blog_posts.og_image_url` updated async after publish
- [ ] Custom template upload (Agency plan+)

### A/B Form Testing
- [ ] `a_b_test_enabled` toggle per form
- [ ] Variant B schema editor in dashboard
- [ ] Widget randomly assigns visitor to A or B (50/50 default)
- [ ] Submissions tagged with `a_b_variant`
- [ ] A/B results dashboard: conversion rate by variant

### Lead Tagging & Segmentation
- [ ] Tag management (create, colour-code, delete)
- [ ] Bulk tag submissions from list view
- [ ] Auto-tag rules: if `utm_source = google` → tag "Google Organic"
- [ ] Filter submissions by tag

### Weekly Digest Email
- [ ] `weekly_digest` template (top stats, new leads summary)
- [ ] Opt-in toggle in notification settings
- [ ] Scheduled job: every Monday 9 AM IST

### API Key Access
- [ ] Regeneratable `fm_` project API keys
- [ ] Read-only API key for partner/agency access
- [ ] `GET /api/v1/projects/{id}/submissions` accessible via API key

### Infrastructure Hardening
- [ ] Connection pooling: Neon's built-in PgBouncer or pgBouncer sidecar
- [ ] Background job: hash IP addresses older than 30 days
- [ ] Background job: retention enforcement (delete rows > project.retention_days)
- [ ] Background job: cleanup expired ghost leads
- [ ] Background job: auto-disable webhooks with failure_count > 10
- [ ] Logfire / Pydantic Logfire for observability

### Enterprise Plan
- [ ] ₹3,499/month Enterprise plan
- [ ] Custom domain for blog (CNAME verification flow)
- [ ] White-label widget (remove "Powered by FormNest" badge)
- [ ] Priority email support SLA

### ✅ Phase 3 Done When
- ₹30K MRR
- Programmatic SEO in production (agencies using it)
- At least 2 Enterprise customers
- Infrastructure running smoothly with no manual interventions

---

## 6. Phase 4 — WBSP Bridge (Months 10–18)

**Revenue Gate:** ₹50K MRR (combined FormNest + WBSP) before Phase 5

**Goal:** Connect FormNest leads to WBSP WhatsApp. Prove the merger value proposition.

### BridgeService Implementation
- [ ] `BridgeService.sync_contact(submission)` in Submission Worker
- [ ] Read `email`/`phone` from `form_submission_index`
- [ ] `POST /api/v1/workspaces/{wbsp_id}/contacts` — WBSP internal API
- [ ] Upsert logic: find by email/phone → update, else create
- [ ] Tag synced contact with `formnest_lead` tag in WBSP
- [ ] Store `wbsp_contact_id` back in `form_submission_index`

### WBSP Integration UI in FormNest
- [ ] "Connect WhatsApp (WBSP)" option in project integrations
- [ ] OAuth-style auth flow between FormNest ↔ WBSP using shared Supabase token
- [ ] "WhatsApp this lead" button in submission detail view
- [ ] Opens WBSP conversation for that contact (deep link)

### WBSP Codebase Changes
- [ ] `formnest_contact_sources` table (see DATABASE_SCHEMA.md)
- [ ] Contact profile shows FormNest form submissions panel
- [ ] "Source: FormNest – Contact Us form" visible in WBSP CRM

### Shared Billing Experiment
- [ ] Unified pricing page: "FormNest + WhatsApp Bundle"
- [ ] Bundle plan: ₹2,499/month covers both products
- [ ] Billing handled in FormNest (WBSP gets revenue share)

### ✅ Phase 4 Done When
- FormNest leads automatically syncing to WBSP contacts
- At least 10 customers using the WhatsApp follow-up feature
- Bundle plan has at least 5 subscribers
- Zero data inconsistencies between FormNest and WBSP contacts

---

## 7. Phase 5 — Unified Platform (Months 18–24)

**Goal:** Single product. One workspace. One subscription. FormNest + WBSP = Growth Platform.

### Unified Workspace
- [ ] Single login → see both FormNest projects and WBSP workspaces
- [ ] Projects and Workspaces merged into unified "Workspace" concept
- [ ] Shared navigation: Forms | WhatsApp | Blog | CRM | Analytics

### Unified CRM
- [ ] Contacts table: sourced from FormNest submissions + WBSP conversations
- [ ] Contact timeline: "Filled contact form" → "WhatsApp conversation started" → "Converted"
- [ ] Unified tagging across both systems
- [ ] Lead scoring (Phase 5): score based on form fields + WhatsApp engagement

### Full Growth Loop
- [ ] Programmatic SEO page → embedded FormNest form → auto WhatsApp follow-up → campaign → conversion tracking
- [ ] Funnel analytics: page views → form opens → submissions → WhatsApp replies → conversions

### Unified Billing
- [ ] Single Razorpay subscription per workspace
- [ ] Module-based pricing: Forms module + WhatsApp module
- [ ] Annual billing discount (20%)
- [ ] Enterprise: custom pricing, dedicated support

### Infrastructure Consolidation
- [ ] Both products on Azure Container Apps (same infra as WBSP scale plan)
- [ ] Shared Redis namespace (separated by `fn:` and `wbsp:` prefixes)
- [ ] Shared PostgreSQL cluster (Neon Business or Azure Flexible Server)
- [ ] Single Supabase project (already shared from Day 1)

### ✅ Phase 5 Done When
- Unified product shipped at `app.growthplatform.in` (or new brand)
- ₹1L MRR (combined)
- At least 20 customers on unified billing
- Full merger docs written and development team onboarded

---

## 8. Milestone Summary

| Milestone | Target Date | Success Metric |
|---|---|---|
| Phase 0 complete | Week 4 | Local dev loop working |
| Alpha launch (private) | Week 8 | 5 developer beta users |
| Public launch | Week 12 | Live at app.formnest.in |
| First customer | Month 3 | ₹449 first payment |
| ₹10K MRR | Month 6 | Phase 3 gate |
| ₹30K MRR | Month 9 | Phase 4 gate |
| WBSP bridge live | Month 14 | Leads syncing to WhatsApp |
| ₹50K MRR (combined) | Month 18 | Phase 5 gate |
| Unified platform beta | Month 21 | 10 unified customers |
| ₹1L MRR | Month 24 | Scale milestone |

---

## 9. Feature Backlog

Features tracked but not scheduled for any current phase. Prioritise based on customer demand.

### High Priority Backlog
- **Slack integration** — post new submission to Slack channel
- **Airtable sync** — append rows to Airtable base
- **File upload field** — upload to Cloudflare R2, stored as media_files
- **Rating field type** — star rating input
- **Form embed in blog posts** — embed a form inside any blog post
- **Zapier / Make (Integromat) native app** — for non-technical users
- **Conditional logic (advanced)** — show/hide entire steps based on earlier answers
- **Email field verification** — OTP verify before form submit (for high-value forms)

### Medium Priority Backlog
- **Multi-language widget** — i18n for Hindi, Tamil, Telugu, Marathi form labels
- **Custom domain for forms** — serve `/f/{key}` from client's own domain
- **Form response PDF** — auto-generate PDF receipt for submitter
- **Submission notes** — internal notes on a submission (like CRM notes)
- **Form duplication** — clone form with same schema
- **Bulk CSV import** — import leads from CSV into submission index
- **IP allowlist** — restrict form submissions to specific IP ranges

### Low Priority Backlog
- **Mobile app (React Native)** — push notification on new submission
- **Team chat** — internal comments on submissions (like Intercom inbox)
- **Hubspot CRM sync** — for enterprise customers who already use Hubspot
- **Lead scoring ML model** — rank leads by conversion likelihood
- **Heatmap analytics** — click + scroll heatmaps on embedded forms
- **White-label reseller program** — agencies resell FormNest under their brand

---

## 🔗 Related Documentation

- **[Architecture Overview](ARCHITECTURE.md)** — System design, component patterns, WBSP merger strategy
- **[Database Schema](DATABASE_SCHEMA.md)** — Complete table definitions and indexes
- **[WBSP Architecture](../wbsp/docs/architecture/ARCHITECTURE.md)** — TREEEX-WBSP system design (merger target)

---

*FormNest Project Roadmap v1.0 · Manovratha Tech · Shashank*
*Last updated: 2026 · Target: ₹1L MRR by Month 24*
