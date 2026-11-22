# Product Requirements Document — Phase 0 draft

> Status: DRAFT for review. Assumptions are marked A#; open decisions at the end. Platform capabilities are DOCUMENTED-only, never live-verified (see `../api/API_FEASIBILITY.md`).

## 1. Problem and audience
Shopee affiliate creators run several Facebook Pages and repeat the same work per product: collect product + affiliate link, build a short vertical video, schedule it, post, add the affiliate link, check that it worked. The product automates this with verifiable per-item status.

Assumptions
- A1 Target market Thailand (Shopee TH). A2 UI English first, Thai later. A3 Product ingest is manual entry or CSV first; no scraping (ADR-0004). A4 Meta and Shopee API access may be delayed or denied; every external step has a manual fallback. A5 Affiliate URLs are supplied by the user or generated through an approved Shopee API only.

## 2. Actors and roles
| Actor | Type | Can |
|---|---|---|
| Owner | internal | Everything incl. delete workspace, manage members, connect/disconnect Pages |
| Admin | internal | Manage products, videos, campaigns, approvals, connect Pages; cannot delete workspace or change owner |
| Member | internal | Create/edit products, videos, draft campaigns; cannot publish without approval, cannot connect Pages |
| Meta (Graph API) | external | Auth, Page tokens, Reels, comments |
| Shopee Affiliate | external | Affiliate links, optional product API |

(Role matrix is a proposal; see open decisions.) Membership is per workspace (organization); a user may belong to many.

## 3. Personas
- **Nok, solo affiliate** — 1–2 Pages, 20 products/week, wants fewer clicks and to see which posts failed.
- **Ploy, small team lead** — 5 Pages, 3 teammates; needs approval before posting and an audit trail.
- **Arm, agency admin** — multiple client workspaces; needs strict separation of data and tokens.

## 4. Journey
1. **Import** products (manual/CSV) with image rights flag → 2. **Affiliate URL** saved per product (user-provided; origin recorded) → 3. **Video** rendered from template (15/20/30 s) → 4. **Campaign**: products × Pages, caption, time slot, approval → 5. **Publish** Reel to Page (async job) → 6. **Comment** with affiliate link (after video published) → 7. **Verify**: remote video id/URL stored, status reconciled, partial failures shown.

## 5. Status model (user-facing)
Video publish and affiliate comment are independent.

| Layer | Statuses | User wording |
|---|---|---|
| Product | draft, ready | — |
| Render | queued, rendering, ready, failed | "Video ready / Render failed — retry" |
| Campaign item | draft, awaiting_approval, scheduled, running, done, partial, failed, cancelled | — |
| `video_publish_status` | queued, starting, uploading, finishing, processing, published, failed, unknown, failed_safe_to_retry | "Publishing…", "Reel published ✓", "Checking with Facebook…" (unknown), "Failed — safe to retry" |
| `affiliate_comment_status` | not_requested, pending, posting, posted, failed, unknown, skipped | "Comment posted ✓", "Comment failed — retry", "Checking comment…" |

Combined examples: *Reel published ✓ / Comment failed — retry* (campaign item = `partial`); *Checking with Facebook… (no retry until verified)*.
`unknown` is never retried blindly; the system or user triggers **Check status** (reconcile).

## 6. Scope
In (Phases 0–5): workspaces and roles; manual/CSV products; affiliate URL storage; FFmpeg image-based templates; Meta Page connection (test mode first); Reels publish; permitted affiliate comment; scheduling; retry/reconcile; approvals; job monitor; audit log.
Out: Shopee Video basket tagging; scraping or session/token extraction; guaranteed Meta/Shopee approval; Google Trends/Veo/Gemini; TikTok/Instagram/YouTube; billing (Phase 6); Chrome extension (later, only where permitted).

## 7. Acceptance scenarios
1. Given workspaces A and B, when A imports products, then B cannot list or fetch them (API returns 404).
2. Given a product with authorized images, when the user renders, then an MP4 H.264/AAC 1080×1920, 30 fps, 15 s (or chosen template) is produced and passes ffprobe checks.
3. Given a connected Page and a ready video, when publishing, then the remote video id is stored right after upload start and the final state is reconciled from Meta after any ambiguous timeout.
4. Given a published Reel, when the comment call fails, then the Reel stays "published" and the comment shows "failed — retry".
5. Given a scheduled campaign item, when the worker retries or runs twice, then only one Reel exists on the Page (idempotency key).
6. Given a member (not admin), when they submit a campaign requiring approval, then it stays `awaiting_approval` and nothing is posted.
7. Given a publish call that times out, when the user opens the Job Monitor, then the item shows "Checking with Facebook…" and Retry is disabled until reconcile finishes.
8. Given reconcile finds the Reel already published, then status becomes published and no new upload occurs.
9. Given a CSV with a duplicate source URL within the workspace, when imported, then the duplicate is skipped and reported, not duplicated.
10. Given an expired/revoked Page token, when publishing, then the item fails with "Reconnect Page" and no data leaks into logs.
11. Given a Page that already has 30 API-published Reels in 24 h, when scheduling another, then the item is delayed with a clear message (Meta documented cap).
12. Given a user disconnects a Page, then stored tokens are deleted and pending items for that Page are paused.

## 8. Sitemap (MVP subset of ROADMAP §14)
- `/login`, `/onboarding` (create workspace)
- `/` Overview (counts + pipeline)
- `/products` Product Library; `/products/import` (manual/CSV); `/products/{id}`
- `/videos` Video Studio (templates, render, gallery)
- `/campaigns`, `/campaigns/new` Campaign Builder; `/calendar` Publishing Calendar
- `/jobs` Job Monitor; `/jobs/{id}`
- `/settings/accounts` Connected Accounts; `/settings/members`
- Later: Billing/Usage, Admin Console, Trend Explorer, Analytics.

## 9. Low-fi wireframes

### Product Library
```
+------------------------------------------------------------------+
| Products                         [Import CSV] [+ Add product]    |
| Search [__________]  Tag [all v]  Rights [all v]                 |
+---+--------+----------------------+---------+-----------+--------+
|[] | img    | Name                 | Price   | Affiliate | Video  |
+---+--------+----------------------+---------+-----------+--------+
|[] | [img]  | Wireless earbuds     | 399 THB | shope.ee/.. OK | ready  |
|[] | [img]  | Phone case           | 99 THB  | missing !  | -      |
|[] | [img]  | Desk lamp            | 259 THB | shope.ee/.. OK | failed |
+---+--------+----------------------+---------+-----------+--------+
| 3 selected: [Render video] [Add to campaign] [Edit tags]         |
+------------------------------------------------------------------+
```

### Campaign Builder
```
+------------------------------------------------------------------+
| New campaign: [Name______]          Status: Draft                |
| 1 Products   [Pick from library]  (12 selected)                  |
| 2 Pages      [x] Shop Page A  [x] Shop Page B  [ ] Page C        |
| 3 Caption    [Template text with {name} {price}______________]   |
|    Affiliate comment: [x] post link as comment  disclosure [x]   |
| 4 Schedule   Start [2026-12-01 18:00]  every [30] min            |
|    Page cap: 30 Reels/24h (Meta)                                 |
| 5 Approval   [x] require admin approval                          |
| ---------------------------------------------------------------- |
| Estimated jobs: 24   Warnings: 2 products without video          |
|                      [Save draft] [Submit for approval]          |
+------------------------------------------------------------------+
```

### Job Monitor
```
+------------------------------------------------------------------+
| Jobs      Status [all v]  Page [all v]  Date [today v]           |
+------+------------+--------+----------------+-------------+------+
| Item | Product    | Page   | Video          | Comment     | Act  |
+------+------------+--------+----------------+-------------+------+
| #101 | Earbuds    | Pg A   | Published OK   | Posted OK   | link |
| #102 | Phone case | Pg A   | Published OK   | Failed !    |[Retry comment]|
| #103 | Desk lamp  | Pg B   | Checking...    | -           |[Check status]|
| #104 | Mug        | Pg B   | Failed (safe)  | -           |[Retry]|
+------+------------+--------+----------------+-------------+------+
| #102 detail: attempts (time, phase, outcome, correlation id),    |
|              remote video id, permalink                          |
+------------------------------------------------------------------+
```

## 10. Non-functional requirements
Tenant isolation at DB and API layer; encrypted provider tokens, revocation on disconnect; no secrets in logs; structured logs with correlation IDs; every external call recorded as an immutable attempt; advertising disclosure and image-rights flags carried through to publishing; clear user messages on partial failure.

## 11. Open decisions
1. Role matrix details (can members publish?).
2. Business model, pricing, plans (Phase 6).
3. Shopee API vs manual-only ingest depending on eligibility (B2).
4. Meta login flavor (Login vs Login for Business) and app type.
5. Reel as comment target; reel description link vs comment link (B5).
6. Affiliate disclosure wording (legal) and music licensing.
7. Hosting region and data retention for media.
8. Whether campaigns auto-post or always require approval by default.
