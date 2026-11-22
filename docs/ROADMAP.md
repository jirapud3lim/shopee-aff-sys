# Shopee Affiliate Automation SaaS — Development Roadmap & Master Checklist

> Version: 1.0  
> Prepared: 2026-11-22  
> Status: Planning / Not started  
> Goal: Build a multi-tenant SaaS with AffiFlowApp-like **Shopee Affiliate → Facebook Reels** capabilities first; later add Google Trends, Gemini/Veo, and multi-platform publishing.

## 0. Scope, principles and critical assumptions

**MVP target (Phases 0–5):** Import Shopee product data and affiliate URLs, create short vertical videos from product images, connect Facebook Pages using authorized Meta OAuth, schedule and publish Reels, add/verify affiliate-link comments where permitted, and monitor individual jobs and errors. Phase 6 enables commercial SaaS use. Phases 7–8 add AI discovery/video and further social networks.

**Important constraints:**
- Shopee Affiliate link generation/API access depends on account eligibility, authorization and platform terms. Support user-provided affiliate URLs and CSV imports as fallbacks.
- Shopee Video **affiliate product basket tagging** is *not* part of the verified initial MVP; seller-oriented Shopee video upload tools do not automatically imply third-party Affiliate basket integration.
- Meta OAuth scopes, Page Reels Publishing, comments, rate limits, App Review and production permissions must be tested with official current documentation and approved accounts. Never claim feature parity before live end-to-end verification.
- Google Trends reflects search interest, *not* Shopee sales. Product-to-trend matching needs its own logic/data.
- Google Flow UI does not necessarily expose suitable bulk automation APIs. For automated AI video use an officially available Google Cloud/Vertex AI Veo endpoint and confirm its region, quota, pricing and terms.
- Use only product images/content that may lawfully be reused; comply with Shopee/Meta policies and disclosure rules. Obtain rights to music and other third-party assets.
- Prefer a **modular monolith** plus background job workers, rather than microservices at the outset.

## 1. Roadmap overview

| Phase | Focus | Rough engineering effort* | Exit milestone |
|---|---|---|---|
| 0 | Requirements, feasibility, API access | 3–5 working days | PRD + proven/blocked API paths |
| 1 | SaaS foundation | 1–2 weeks | Authenticated isolated workspaces |
| 2 | Product collection + affiliate library | 1–2 weeks | Reliable product import and links |
| 3 | Content & video studio | 2–3 weeks | Batch FFmpeg videos |
| 4 | Facebook integration | 1–3 weeks + external review | Authorized Reel post + status + comment handling |
| 5 | Bulk campaigns and automation | 2–3 weeks | End-to-end core MVP |
| 6 | Billing and productionization | 2–3 weeks | Commercial beta readiness |
| 7 | Google Trends / Gemini / Veo | 2–4 weeks | AI-assisted product-to-video pipeline |
| 8 | More platforms and scaling | Ongoing | Provider integrations + analytics |

*Planning estimates only; exclude external approvals and unpredictable engineering/rework. Phases can overlap where dependencies permit.

## 2. Proposed technical stack

| Layer | Initial choice | Responsibilities |
|---|---|---|
| Web UI | Next.js + TypeScript | Dashboard, product library, studio, calendar, monitoring |
| UI components | Tailwind CSS + shadcn/ui | Responsive UI and reusable component system |
| Backend | FastAPI (Python) | API and business logic |
| Data access | SQLAlchemy + Alembic | Database models and migrations |
| Database | PostgreSQL | Tenant, user, product, campaign, job, billing data |
| Cache/queue broker | Redis | Celery broker, ephemeral state, caching |
| Job workers | Celery + Celery Beat | Render, publish, comment, sync, retry and scheduling |
| Video rendering | FFmpeg | Render template-based 9:16 MP4 videos |
| Media store | Cloudflare R2 or S3-compatible object store | Product images, generated video, thumbnails |
| Product capture | Chrome Extension Manifest V3 + CSV | Authorized input and bulk import |
| Social publishing | Meta Graph API | OAuth, Pages, Reels, comments as authorized |
| Future generative AI | Gemini API + Google Cloud Veo | Scripts, prompts, image-to-video |
| Monitoring | Sentry + structured logging/metrics | Tracing failures, alerting, observability |
| Deployment | Docker + hosting provider | Repeatable dev/staging/production environments |
| Payments | Suitable Thai-friendly payment provider (select in Phase 6) | Subscription and payment lifecycle |

### Suggested repo layout

```text
affiliate-saas/
├── apps/
│   ├── web/                        # Next.js
│   └── extension/                  # Chrome MV3
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── tenants/
│   │   │   ├── products/
│   │   │   ├── affiliates/
│   │   │   ├── content/
│   │   │   ├── campaigns/
│   │   │   ├── publishing/
│   │   │   ├── billing/
│   │   │   └── analytics/
│   │   ├── integrations/
│   │   │   ├── meta/
│   │   │   ├── shopee/
│   │   │   └── google/
│   │   └── workers/
│   ├── migrations/
│   └── tests/
├── infra/
│   ├── docker/
│   └── deployment/
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── api/
│   ├── decisions/
│   └── phases/
└── docker-compose.yml
```

## 3. Phase 0 — Planning & API feasibility

**Objective:** Prove the riskiest external integrations before implementing the whole product.

### Preparation
- [ ] Create and verify a Shopee Affiliate test account.
- [ ] Prepare 10+ real test products with images, product URLs and affiliate links.
- [ ] Create Meta for Developers account, Meta App and test Facebook Page(s).
- [ ] Establish Git repository, issue tracker and development environment.
- [ ] Read latest Shopee Affiliate terms, API eligibility and product-data reuse policies.
- [ ] Read latest Meta Page Reels, OAuth, Page/comment permissions, platform policy and App Review documentation.
- [ ] Identify permitted sources of product images, music and marketing assets.

### Engineering tasks
- [ ] Write PRD: target users, use cases, supported channels, in/out of scope.
- [ ] Define personas and roles: owner, admin, member.
- [ ] Map full journey: import → affiliate URL → video → campaign → publish → comment → verify.
- [ ] Define business events, failure behavior and user-facing status model.
- [ ] Create architecture diagram, initial ERD and initial API contracts.
- [ ] Prototype Meta OAuth and retrieve authorized Pages.
- [ ] Test one real Page Reel publish through current official API.
- [ ] Test posting and reading an affiliate-link comment (where permitted).
- [ ] Test publishing idempotency/reconciliation behavior after ambiguous timeouts.
- [ ] Verify product capture/import path and optional Shopee API eligibility.
- [ ] Define video spec: MP4, H.264, 1080×1920, vertical 9:16, template durations 15/20/30 s.
- [ ] Record dependencies, costs, blockers and alternatives in an API feasibility report.

**Deliverables:** `docs/product/PRD.md`, `docs/architecture/SYSTEM.md`, `docs/architecture/ERD.md`, `docs/api/API_FEASIBILITY.md`, backlog, sitemap, wireframes.

**Acceptance criteria:** Feasible, authorized end-to-end paths are demonstrated or documented as blockers with fallbacks; no unsupported assumption is silently treated as solved.

## 4. Phase 1 — SaaS foundation

**Objective:** Secure multi-tenant web app, API, persistence and deployment foundation.

### Frontend
- [ ] Create Next.js + TypeScript project and set up UI theme/tokens.
- [ ] Implement responsive app shell, sidebar, top bar and workspace switcher.
- [ ] Implement register, sign-in, sign-out and password reset.
- [ ] Implement profile and workspace settings screens.
- [ ] Implement consistent loading, empty, error and permission-denied states.
- [ ] Create sitemap/navigation placeholders for future modules.

### Backend/data
- [ ] Bootstrap FastAPI with versioned API routes and OpenAPI docs.
- [ ] Add PostgreSQL, SQLAlchemy, Alembic and migration CI checks.
- [ ] Create `users`, `organizations`, `organization_members`, `sessions`, `audit_logs`.
- [ ] Implement session/security controls, password hashing and account verification.
- [ ] Implement organization lifecycle and workspace invitations.
- [ ] Implement role-based access controls on the server.
- [ ] Apply organization scoping to all tenant-owned tables and API queries.
- [ ] Add request validation, consistent error contracts and pagination.
- [ ] Add structured logs, correlation IDs and exception tracking.
- [ ] Set up Docker Compose for local dev; create staging deployment.
- [ ] Add automated unit, integration and tenant-isolation tests.

**Acceptance criteria:** Users register/login, create/switch workspaces and cannot access another tenant's resources. Staging deploy and schema migrations are repeatable.

## 5. Phase 2 — Product collector & affiliate library

**Objective:** Reliable data ingestion and product inventory for downstream content creation.

### Product management
- [ ] Implement manual product entry/edit and validation.
- [ ] Create `products`, `product_images`, `affiliate_links`, `product_import_batches`, `product_snapshots`.
- [ ] Build product grid/table view with filter, search, sort, pagination and tags.
- [ ] Support source URL, affiliate URL, product name, price/currency, category and multiple images.
- [ ] Store original and last-verified values separately to avoid stale-price claims.
- [ ] Add product image thumbnails and gallery.
- [ ] Implement duplicate detection and merge/update decisions.
- [ ] Add bulk select/edit/archive/export operations.
- [ ] Add product readiness/completeness indicators for video generation.

### Import and extension
- [ ] Implement CSV/Excel sample templates and mapping UI.
- [ ] Validate rows, preview errors, report duplicates and show import summary.
- [ ] Support import retry and downloadable error reports.
- [ ] Design Chrome MV3 extension (minimum permissions).
- [ ] Capture only authorized product information; send securely to backend API.
- [ ] Validate extension behavior against website terms; do not bypass CAPTCHA/auth controls.
- [ ] Keep manual input and CSV as primary fallbacks for unsupported sources.
- [ ] Optionally integrate an authorized Shopee affiliate API only after approval.

**Acceptance criteria:** Import 100 test products reliably, detect duplicates, retain affiliate links, and enforce tenant isolation.

## 6. Phase 3 — Content studio & template video engine

**Objective:** Convert product images into short vertical marketing videos at scale, without depending on paid AI video APIs.

### Video and content
- [ ] Define provider interface (`VideoProvider`) and request/result schema.
- [ ] Implement `FFmpegVideoProvider` as initial engine.
- [ ] Build template model: text layers, scenes, transitions, durations, themes, music.
- [ ] Create `video_templates`, `video_projects`, `video_scenes`, `video_assets`, `render_jobs`.
- [ ] Support product selection and batch generation.
- [ ] Validate and normalize input images before rendering.
- [ ] Implement vertical 9:16 MP4/H.264 export, configurable frame rate and resolution.
- [ ] Implement pan/zoom, fade/slide, overlays, title cards, price labels and CTA.
- [ ] Add licensed background-music selection and optional mute.
- [ ] Build browser preview, progress indicator and download action.
- [ ] Generate thumbnails, metadata and render artifact checksums.
- [ ] Add captions and hashtag editing; optional Gemini-generated text after API setup.
- [ ] Add render cancellation, retry, deduplication and error reporting.

### Worker/media infrastructure
- [ ] Configure Redis and separate Celery render queue/workers.
- [ ] Integrate object storage with signed URLs and retention policy.
- [ ] Track rendering time, CPU/RAM demand, storage size and unit cost.
- [ ] Put resource caps and concurrency limits on the rendering workers.
- [ ] Provide test fixtures for invalid images, long titles and broken fonts.
- [ ] Add quality/review step for factual product claims and licensed assets.

**Future compatibility:** `GoogleVeoProvider` is only an interface at this stage. Use official Cloud API later, not browser automation of Google Flow.

**Acceptance criteria:** Generate 100 valid vertical videos in a test batch with tracked statuses, retries, storage links and human review. Confirm capacity with actual infrastructure.

## 7. Phase 4 — Meta OAuth & Facebook Reels publishing

**Objective:** Authorized Page connections and reliable publishing to Facebook Reels.

### Account connection
- [ ] Configure Meta App, redirect URLs, data-use/privacy pages and webhook/security settings as appropriate.
- [ ] Implement OAuth flow with CSRF/state validation.
- [ ] Request and validate the minimum current API permissions needed.
- [ ] List and select Pages accessible to the connected user.
- [ ] Store credentials encrypted; track scopes, expiry, revocation and reconnect needs.
- [ ] Implement connect/disconnect and permission-health dashboard.
- [ ] Prepare Meta App Review evidence and business verification if applicable.

### Reels and comments
- [ ] Implement current official upload/start/finalize flow for Page Reels.
- [ ] Validate video constraints and caption before sending.
- [ ] Save remote IDs, post URL, provider responses and sanitized errors.
- [ ] Implement publish-status polling/reconciliation.
- [ ] Add optional affiliate-link comment workflow if permitted by scopes/policies.
- [ ] Track video publish and comment post statuses independently.
- [ ] Prevent blind retries when timeout leaves unknown remote state.
- [ ] Handle token failures, rate limits, permission changes and media rejection.
- [ ] Add disconnect/revoke flow and appropriate retention/deletion behavior.

**Acceptance criteria:** With approved test access, connect Page → upload Reel → verify published URL → post/verify comment (if approved) → capture status and failure details. Document restrictions for public users.

## 8. Phase 5 — Bulk campaigns, scheduler & automation

**Objective:** Core AffiFlowApp-style bulk workflow and job observability.

### Campaign UI
- [ ] Build Campaign Builder: choose products, videos, pages and timing.
- [ ] Add campaign draft, review, approve, activate, pause, resume and cancel.
- [ ] Support target-specific captions and affiliate links.
- [ ] Build scheduling calendar and timezone-safe schedule editor.
- [ ] Support per-Page posting limits, cooldowns and conservative pacing.
- [ ] Show total estimated jobs before activation.

### Execution engine
- [ ] Create `campaigns`, `campaign_items`, `publish_jobs`, `publish_attempts`, `post_comments`.
- [ ] Define explicit job state machine and legal transitions.
- [ ] Suggested states: DRAFT → VALIDATED → SCHEDULED → QUEUED → UPLOADING → PUBLISHING → VERIFYING → PUBLISHED → COMMENT_PENDING → COMPLETED.
- [ ] Handle FAILED, RETRY_WAITING, CANCELLED and NEEDS_ATTENTION.
- [ ] Implement durable scheduler using database as the source of truth.
- [ ] Configure separate Celery queues: `render`, `publish`, `comment`, `reconcile`, `analytics`.
- [ ] Implement idempotency keys, uniqueness constraints and reconciliation checks.
- [ ] Retry transient failures with bounded exponential backoff and jitter.
- [ ] Never automatically repeat an ambiguous publish without reconciling remote status.
- [ ] Implement dead-letter handling/manual retry for permanent failures.
- [ ] Support concurrency controls per tenant, Page and platform.
- [ ] Add status updates, searchable logs and progress counters.
- [ ] Record remote published URL and comment result separately.

### Reliability/QA
- [ ] Test simulation: 100 products × 5 Pages = 500 jobs (not a claim of provider-permitted rate).
- [ ] Test worker restarts, network outages and delayed API responses.
- [ ] Test pause/resume and schedule cancellation.
- [ ] Verify no duplicate remote posts in timeout/retry test cases.
- [ ] Validate tenant/job access controls and user-visible failure recovery.

**Acceptance criteria:** Manage and observe a 500-job *staging workload*, with correct scheduling, error categorization and no unintentional duplicate publish under test. Live rates depend on Meta limits.

**Milestone:** Core MVP ready for controlled beta, subject to live API permissions and policy compliance.

## 9. Phase 6 — Commercial SaaS, billing and production readiness

**Objective:** Enable multiple paying customers with transparent usage quotas, support and security.

### Plans and payments
- [ ] Define billable units: pages, videos rendered, publish jobs, AI credits, storage.
- [ ] Select payment provider with Thai payments/subscriptions/tax support.
- [ ] Create `subscriptions`, `plans`, `usage_events`, `payments`, `invoices` as needed.
- [ ] Implement trial and paid subscription lifecycles.
- [ ] Implement plan upgrade/downgrade/cancel and proration policy.
- [ ] Handle payment webhooks with signature verification and idempotency.
- [ ] Enforce usage quotas server-side using a ledger; not client-side counters.
- [ ] Add billing overview, invoices/payment history and warning notifications.

### Operations and compliance
- [ ] Build internal admin dashboard, tenant support and audit trails.
- [ ] Publish Terms, Privacy Policy, data deletion instructions and support contact.
- [ ] Review applicable PDPA/privacy, affiliate disclosures and provider policies.
- [ ] Configure production secrets, least-privilege IAM and key rotation.
- [ ] Add database backups, restore drills, storage retention and deletion policies.
- [ ] Add metrics/dashboards, alerting, incident runbooks and health checks.
- [ ] Add CI/CD with test gates, migration plan and rollback procedure.
- [ ] Conduct security review, abuse prevention and load tests.
- [ ] Prepare controlled beta/onboarding documentation.

**Illustrative, unvalidated pricing hypotheses (not market-verified):** Starter ฿299/mo (1 Page, 100 videos, 100 posts), Pro ฿799/mo (5 Pages, 500 videos, 1,000 posts), Business ฿1,990/mo (20 Pages, 2,000 videos, 5,000 posts). Validate unit economics and platform limits before using these prices.

**Acceptance criteria:** Customer signup → plan selection → payment → entitlement enforcement → cancellation works; security, support, backups and monitoring are production-ready.

## 10. Phase 7 — Google Trends, Gemini and Veo

**Objective:** Discover trending demand, match relevant products, and generate AI-enhanced marketing videos.

### Google setup (do this now only if AI is needed earlier)
- [ ] Create Google Cloud project and billing account.
- [ ] Configure budget alerts, IAM, service identities and API secrets.
- [ ] Confirm available Gemini and Veo services, supported regions, model names, pricing and quotas.
- [ ] Apply for quotas/access if necessary; test a single low-cost API call first.
- [ ] Define approval and cost caps before running bulk generative jobs.

### Trends/product discovery
- [ ] Determine compliant Trends ingestion (official integrations or appropriately permitted exports/feeds; validate availability).
- [ ] Build Trend Explorer for Thai location, category, timeframe and keywords.
- [ ] Normalize keywords and match them with imported Shopee products.
- [ ] Build explainable opportunity score combining trend signal, product relevance and trusted product metrics.
- [ ] Display source timestamp, freshness and limitations.
- [ ] Offer manual curation to avoid irrelevant or misleading matches.

### AI content pipeline
- [ ] Implement optional Gemini text provider for captions/scripts/storyboards/prompts.
- [ ] Implement `GoogleVeoProvider` behind existing VideoProvider abstraction.
- [ ] Support image-to-video jobs asynchronously and handle polling/results/expiration.
- [ ] Use FFmpeg to stitch short generated shots into 15–30 s final ads.
- [ ] Add moderation, image fidelity checks, product claims verification and human approval.
- [ ] Track AI provider usage, costs, budget caps and plan-specific quotas.
- [ ] Provide template-video fallback on quota exhaustion, model failure or high cost.
- [ ] Add metrics for approved/rejected content and render cost per asset.

**Acceptance criteria:** Trend → relevant product → validated storyboard → AI/generated or template-based video → approved asset → campaign queue, with auditable cost tracking.

## 11. Phase 8 — Multi-platform integration & scaling

**Objective:** Expand publishing without rewriting campaign semantics.

- [ ] Define `PublishingProvider` contract for auth, validate, upload, publish, status, capabilities and errors.
- [ ] Add Instagram Reels connector after account and permission validation.
- [ ] Add TikTok posting connector after approval and platform review.
- [ ] Add YouTube uploads/Shorts connector with OAuth and quota management.
- [ ] Add Pinterest publishing if relevant.
- [ ] Research Shopee Video Affiliate basket support separately; do not assume seller-video integrations meet this requirement.
- [ ] Add capability flags so UI only offers verified supported actions.
- [ ] Add cross-platform post analytics and source attribution where APIs permit.
- [ ] Add A/B testing for video/caption with compliant rate limits.
- [ ] Improve autoscaling, media CDN, worker capacity, caching and cost observability.
- [ ] Implement per-provider integration and contract tests.
- [ ] Explore conversion/sales analytics only from legitimately authorized attribution sources.

**Acceptance criteria:** New platform adapters deploy without changing core campaign/job architecture; unsupported capabilities are surfaced clearly to users.

## 12. Service/account setup calendar

| Service | Start phase | Purpose | Notes |
|---|---|---|---|
| GitHub/repository | 0 | Source control, CI | Can start free |
| Shopee Affiliate account | 0 | Real affiliate data and tracking URLs | API access may require approval |
| Meta Developer account/app | 0 | Facebook Pages/Reels/comments | Begin feasibility and review early |
| Docker | 1 | Local environment | No subscription required |
| PostgreSQL hosting | 1 / deployment | Database | Local Docker first |
| Redis / worker hosting | 3–5 | Background jobs | Local Docker first |
| Object storage (R2/S3) | 3 | Images/videos | Monitor storage and egress |
| Gemini API | 3 optional / 7 | AI captions/scripts | Optional earlier |
| Google Cloud + Veo API | 7 or earlier for AI-first experiments | Automated image-to-video | Verify billing, quota and model support |
| Payment gateway | 6 | Paid SaaS | Confirm Thai needs |
| Domain + transactional email | 6 (staging earlier optional) | Public site and email | Required before commercial launch |
| Monitoring/Sentry | 1 onward | Errors/operations | Introduce early |

### What to do *before paying for Google AI video*
- [ ] Validate FFmpeg template video workflow end-to-end.
- [ ] Measure average cost per product/content item with realistic video volumes.
- [ ] Decide whether AI-generated motion materially improves conversions or product quality.
- [ ] Create a small Google Veo proof-of-concept, not a bulk subscription commitment.
- [ ] Confirm approved usage of product images in generative output.

## 13. Core data model (initial candidate)

```text
organizations
users
organization_members
sessions
audit_logs
platform_connections
products
product_images
affiliate_links
product_import_batches
product_snapshots
video_templates
video_projects
video_scenes
video_assets
render_jobs
campaigns
campaign_items
publish_jobs
publish_attempts
post_comments
subscriptions
plans
payments
invoices
usage_events
```

**Cross-cutting design constraints:** tenant ownership and RBAC; encryption of OAuth credentials; immutable event logs for external API operations; separate post and comment success; idempotency; timestamp/timezone precision; media lifecycle and signed access; retries only after reconciliation where remote state is uncertain.

## 14. UX/pages to implement

- [ ] Overview dashboard with product, video, scheduled, published and failed counts.
- [ ] Visible end-to-end workflow pipeline: Collect → Prepare → Render → Schedule → Publish.
- [ ] Product Library: table/grid, import, tags, affiliate URL management.
- [ ] Video Studio: templates, scene preview, text, music, batch render, output gallery.
- [ ] Campaign Builder: products × pages, captions, time slots, approvals and estimated jobs.
- [ ] Publishing Calendar: scheduled posts and bulk rescheduling.
- [ ] Job Monitor: per-item status, errors, attempts, remote URLs, retry/reconcile.
- [ ] Connected Accounts: Meta Pages, token/permission health and disconnect.
- [ ] Billing/Usage: plan, quotas, payments, AI credits.
- [ ] Admin Console: accounts, incidents, audit and support.
- [ ] Later Trend Explorer: search terms and matched product candidates.
- [ ] Later Cross-Platform Analytics.

## 15. Recommended implementation sequence / vertical slices

1. **Technical risk spike:** test one authorized Page Reel and comment flow before building a polished UI.
2. **Vertical slice A:** create workspace → import product → save affiliate URL.
3. **Vertical slice B:** product → FFmpeg template → video preview/download.
4. **Vertical slice C:** connect Page → publish one Reel → verify URL → comment (if permitted).
5. **Vertical slice D:** 100 products × 5 Pages = 500 test jobs → scheduling + retries + observability.
6. **Commercial slice:** subscriptions, quotas, support, backups and public onboarding.
7. **AI slice:** Trends → product match → Gemini script → Veo scenes → video approval.
8. **Expansion:** additional publishing providers and analytics.

## 16. Coding/AI-agent working agreements

- [ ] Keep one short phase specification under `docs/phases/PHASE_N.md` with scope, dependencies, tasks and acceptance criteria.
- [ ] Maintain concise ADRs in `docs/decisions/` for architectural decisions and avoid rereading giant Markdown files every session.
- [ ] Keep implementation tasks small enough to independently test and review.
- [ ] Separate core business logic from provider adapters and I/O.
- [ ] Require migrations, automated tests and API contracts for each module.
- [ ] Run lint, type checking, unit and integration tests in CI.
- [ ] Keep secrets and customer data out of prompts, logs and commits.
- [ ] Use test doubles/mocks for Meta/Shopee/Google in CI; reserve live API tests for protected environments.
- [ ] Update the task checklist and documentation only when work is actually verified.
- [ ] Document known limitations and required external approvals visibly.

## 17. Master gates

- [ ] **Gate A — Feasibility:** supported external APIs, permissions and compliance confirmed; blockers documented.
- [ ] **Gate B — Product + Video:** isolated tenant product library and reliable batch video export.
- [ ] **Gate C — AffiFlowApp core parity:** approved Page integration plus trustworthy bulk scheduling, publishing and status monitoring.
- [ ] **Gate D — Commercial beta:** payments, usage controls, policies, backups and monitoring.
- [ ] **Gate E — AI platform:** trends, script, Veo integration, human approval, budget caps.
- [ ] **Gate F — Multichannel:** capabilities verified per provider, analytics and scale tests.

## 18. Immediate next actions

1. [ ] Create Git repository and add this document as `docs/ROADMAP.md`.
2. [ ] Write focused `docs/product/PRD.md` for Phase 0–5 (MVP only).
3. [ ] Create test Shopee Affiliate account and Facebook Page/Meta App.
4. [ ] Run Meta live feasibility spike; log permissions, responses and blockers.
5. [ ] Decide product import MVP: manual entry + CSV first, Chrome extension next.
6. [ ] Implement baseline Next.js/FastAPI/PostgreSQL development environment.
7. [ ] Build one end-to-end vertical slice before adding extra integrations.

---

## Useful official entry points (verify current docs before implementation)

- Meta for Developers: https://developers.facebook.com/
- Meta Graph API: https://developers.facebook.com/docs/graph-api/
- Google Cloud: https://cloud.google.com/
- Vertex AI generative AI documentation: https://cloud.google.com/vertex-ai/generative-ai/docs/
- Google Trends: https://trends.google.com/
- Chrome Extensions Manifest V3: https://developer.chrome.com/docs/extensions/develop/migrate/what-is-mv3
- Shopee Affiliate: use the official Shopee Affiliate portal/help center for the operating country; API access and terms vary by account and region.

> This is an engineering plan, not a representation that Shopee/Meta/Google have granted integration access or confirmed any specific quota. Revalidate API permissions, pricing and platform policies at the time of implementation.
