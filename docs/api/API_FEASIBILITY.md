# External API Feasibility — Phase 0

> Date accessed: 2026-11-22 · Graph API current version at access: **v27.0** (introduced 2026-11-04) · Target market assumed: Thailand (assumption A1).
> Nothing here is LIVE-VERIFIED. No account, token or live call exists yet.

Status labels:
- **DOCUMENTED** — stated in official docs (URL cited), not live-tested.
- **UNVERIFIED** — not found in official docs, or docs conflict/unclear.
- **BLOCKED** — needs an account/approval we do not have.

## 1. Capability / permission matrix

| # | Capability | Provider | Endpoint | Permissions / features | Access level / review | Doc | Status | Fallback |
|---|---|---|---|---|---|---|---|---|
| 1 | Connect Meta account, get user token | Meta | Facebook Login / Login for Business | Login flow; user must be able to perform tasks on Page | Dev Mode: any permission for users with an App role. Live for others: App Review per permission; Advanced Access needs Business Verification | [Pages API overview](https://developers.facebook.com/docs/pages-api/overview), [Permissions](https://developers.facebook.com/docs/permissions/) | DOCUMENTED / BLOCKED (live) | Test mode with role-holders only |
| 2 | List Pages + Page access tokens | Meta | `GET /me/accounts` | `pages_show_list` (plus others below) | App Review for non-role users | [Pages API overview](https://developers.facebook.com/docs/pages-api/overview) ("How it works"), Reels guide | DOCUMENTED | none (core) |
| 3 | Start Reel upload session | Meta | `POST /{page-id}/video_reels` `upload_phase=start` → `video_id`, `upload_url` | `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`; Page token from user with `CREATE_CONTENT` task | App Review for non-role users | [Reels publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing) | DOCUMENTED | Export MP4 for manual upload |
| 4 | Upload bytes | Meta | `POST https://rupload.facebook.com/video-upload/{video-id}` headers `offset`, `file_size` (binary) or `file_url` (public, robots.txt must allow `facebookexternalhit`; Meta CDN URLs rejected); resumable via `offset` = `bytes_transfered` | same | same | same | DOCUMENTED | — |
| 5 | Finish / publish | Meta | `POST /{page-id}/video_reels` `upload_phase=finish`, `video_id`, `video_state=PUBLISHED\|SCHEDULED\|DRAFT`, `description`, `title`, `is_ai_generated`, `scheduled_publish_time` (>10 min, <29 days) → `{"success":true}` | same | same | same | DOCUMENTED. Doc conflict: param table says `upload_phase` "should be `complete`", example uses `finish` — UNVERIFIED which is authoritative; spike uses `finish` | — |
| 6 | Publish status | Meta | `GET /{video-id}?fields=status` → `video_status`, `uploading_phase`, `processing_phase`, `publishing_phase.publish_status` | `pages_read_engagement` (copyright info) | same | Reels guide | DOCUMENTED | — |
| 7 | List Page Reels (reconcile) | Meta | `GET /{page-id}/video_reels` with `since`/`until` → `id`, `updated_time`, `description` | Page token | same | Reels guide | DOCUMENTED (doc says "published" reels; whether unpublished/processing reels are listed is UNVERIFIED) | Reconcile by stored `video_id` only |
| 8 | Post comment as Page | Meta | `POST /{page-post-id}/comments` `message` → comment `id`; author is the Page | `pages_manage_engagement`, `pages_read_engagement`, `pages_read_user_content`; tasks `MODERATE` + `CREATE_CONTENT`. Pages API overview lists "Comment Management" under `pages_manage_engagement`. The comments guide also lists feature "Page Mentioning" (needed for @mentions only — UNVERIFIED whether plain comments need it) | App Review for non-role users | [Comments & @mentions](https://developers.facebook.com/documentation/pages-api/comments-mentions), [Pages API](https://developers.facebook.com/docs/pages-api/) | DOCUMENTED for posts; **UNVERIFIED that a Reel `video-id` is accepted as `{page-post-id}`** | Manual comment with user confirmation |
| 9 | Read comments (reconcile) | Meta | `GET /{object-id}/comments?fields=from,message` | `pages_read_engagement`, `pages_read_user_content`; `id` field requires MODERATE task; Page Public Content Access feature "may be required" | same | [Page Post Comments v27.0](https://developers.facebook.com/docs/graph-api/reference/page-post/comments/) | DOCUMENTED; read-after-write may be delayed for video/GIF comments | — |
| 10 | Links in comments | Meta | — | — | — | Developer Policies: "Don't confuse, deceive, defraud, mislead, spam" ([devpolicy](https://developers.facebook.com/devpolicy/)). No official doc found restricting URLs in API comments. A developer-forum thread reports links rendered as plain text, unresolved | UNVERIFIED (not restricted in docs; delivery/spam filtering unknown) | Put link in reel description; manual comment |
| 11 | `publish_video` permission | Meta | — | Posts guide lists `publish_video` "if publishing a video to the Page"; the Reels guide does not | — | [Posts](https://developers.facebook.com/docs/pages-api/posts) vs Reels guide | UNVERIFIED (docs differ) — request only if live test requires | — |
| 12 | Shopee product offers | Shopee | GraphQL `productOfferV2` | Account credentials | Confirm account access in a live request | [Thai portal](https://affiliate.shopee.co.th/open_api/list?type=product_offer) | DOCUMENTED; live execution unverified | Manual + CSV (ADR-0004) |
| 13 | Shopee short link | Shopee | GraphQL mutation `generateShortLink` with `originUrl` and optional `subIds` | Account credentials | Confirm account access in a live request | [Thai portal](https://affiliate.shopee.co.th/open_api/list?type=short_link) | DOCUMENTED; live execution unverified | User pastes affiliate URL |
| 14 | Shopee API access | Shopee | See [endpoint catalog](SHOPEE_AFFILIATE_ENDPOINTS.md) | Account credentials | User reports Shopee provided API access | [Thai portal](https://affiliate.shopee.co.th/open_api/home) | Account scope and live execution unverified | Manual + CSV |
| 15 | Reuse of product images/data | Shopee | — | Affiliate program terms | — | Terms not publicly readable by us | UNVERIFIED / BLOCKED | Only user-supplied/authorized images; per-image rights flag |
| 16 | Shopee Video basket tagging | Shopee | — | — | — | No public API found | UNVERIFIED — **out of scope** | — |
| 17 | Trends / Veo | Google | — | — | — | Not researched (Phase 7) | FUTURE | FFmpeg templates |

### Notes on review and verification
- DOCUMENTED: apps in Development Mode can request any permission from users with a role on the app; all Page permissions/features need App Review before live use by others; Advanced Access requires Business Verification ([Pages API overview](https://developers.facebook.com/docs/pages-api/overview), [Permissions](https://developers.facebook.com/docs/permissions/)).
- UNVERIFIED: Business Verification timelines, whether our use case qualifies, and whether Facebook Login vs Login for Business is mandatory for new apps (docs say Login for Business is "preferred").
- DOCUMENTED: permissions unused for 90 days must be re-granted by the user (Permissions page).

## 2. Reels video spec (DOCUMENTED, [Reels publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing), v27.0)

| Property | Meta spec | Our template (ADR-0005) | OK? |
|---|---|---|---|
| Container | .mp4 recommended | MP4, `+faststart` | yes |
| Aspect ratio | 9:16 | 9:16 | yes |
| Resolution | 1080×1920 recommended; min 540×960 | 1080×1920 | yes |
| Frame rate | 24–60 fps, fixed | 30 fps CFR | yes |
| Duration | 3–90 s (Page story ≤ 60 s) | 15 / 20 / 30 s | yes |
| Video | H.264 or H.265 (VP9/AV1 supported); 4:2:0; closed GOP 2–5 s; progressive | H.264 High, yuv420p, GOP 2 s closed | yes |
| Audio | AAC-LC, stereo, 48 kHz, ≥128 kbps | AAC-LC stereo 48 kHz 128k (silent track by default) | yes |
| Max file size | not stated in guide | — | UNVERIFIED |
| Rate limit | 30 API-published posts / 24 h moving window per Page, enforced on `POST /{page_id}/video_reels` | enforce ≤ 30/24 h per Page in our scheduler (use a lower soft cap) | DOCUMENTED |
| Other | Reels only to Pages; collaborators 10 invites/Page/24 h; scheduling 10 min–29 days; `is_ai_generated` disclosure flag; sharing/privacy disclosure to app user required; Page reels are public only | Show disclosure UI; expose `is_ai_generated` when AI used (Phase 7) | DOCUMENTED |
| General Graph rate limiting | Page-token calls use Business Use Case limits; usage in `X-App-Usage` header; numbers not extracted | back off on rate-limit codes | UNVERIFIED (numbers) |

Meta Developer Policies (last updated 2026-02-03 per page): [devpolicy](https://developers.facebook.com/devpolicy/) — DOCUMENTED, not analysed clause by clause; legal review before launch.

## 3. Account prerequisites for a real proof (all BLOCKED today)

1. Meta for Developers account (a real Facebook profile).
2. A Meta App (type per current dashboard; use Facebook Login for Business) in Development Mode; add testers/developers via App Roles.
3. A test Facebook Page where the test user has a role granting `CREATE_CONTENT` (+ `MODERATE` for comments) — Admin covers all tasks.
4. Permissions requested and granted in the 2026-11-22 Business Login test: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_manage_engagement`, `pages_read_user_content` (+ `publish_video` only if needed).
5. Business Verification + App Review with screencasts — only before onboarding non-role users (not needed for the Phase 0 proof within Dev Mode, per docs; UNVERIFIED in practice).
6. Public HTTPS redirect URI for OAuth (localhost allowed for dev: UNVERIFIED).
7. A rendered 1080×1920 MP4 (needs ffmpeg — not installed locally).
8. Shopee Affiliate account (Thailand), approved for Open API (AppId/Secret), plus 10+ test products with affiliate links.
9. Written confirmation of Shopee terms on product image/data reuse.

## 4. Costs (all UNVERIFIED unless noted)

- Meta Graph API / Login: no price found in the pages read; treat as free, UNVERIFIED.
- App Review / Business Verification: no fee found in pages read; may require business documents. UNVERIFIED.
- Shopee Open API: no fee found; commission-based program. UNVERIFIED.
- Our own: object storage, compute for FFmpeg, domain/HTTPS for OAuth redirect (Phase 1+).

## 5. Blockers and decisions

| ID | Blocker | Impact | Next action / owner |
|---|---|---|---|
| B1 | Resolved: Meta App and sandbox Page configured | Live OAuth returned the test Page and all five requested Page permissions | Verify Reel and comment on the sandbox Page |
| B2 | Shopee operations documented; live account scope unverified | Cannot confirm live import or short-link calls | Verify when the integration resumes; use manual + CSV (ADR-0004) |
| B3 | Shopee terms on image reuse unread | Rights risk for rendered videos | User reads terms/asks support; per-image rights flag in data model |
| B4 | Resolved: sample rendered with FFmpeg 9.0.2 | ffprobe verified the 15-second 1080×1920, 30 fps H.264/AAC fixture | Use the synthetic fixture for live publishing |
| B5 | Reel-as-comment-target unverified | Comment step may need different object id | First live test: comment on returned `video_id`, else on post id from video's `permalink_url`/post fields |
| B6 | Meta docs internally inconsistent (`complete` vs `finish`, `publish_video`, v18/v22/v27 examples) | Wrong params | Confirm in first live call; keep adapter versioned and configurable |
| B7 | App Review / BV timeline unknowable | Public launch gate | Start early; MVP can run with role-holders only |

Fallbacks keep the product usable: export MP4 for manual upload, manual comment with confirmation, manual/CSV product + affiliate URL entry.

## 6. Evidence log (no tokens)

| Date | Reviewer | Item | Source (URL, version) | Result | Label |
|---|---|---|---|---|---|
| 2026-11-22 | Sidekick (agent) | Current Graph API version | https://developers.facebook.com/docs/graph-api/changelog | v27.0 latest (2026-11-04); v26.0 2026-07-29; v25.0 until 2028-07-29 | DOCUMENTED |
| 2026-11-22 | Sidekick | Reels flow, specs, rate limit, status, list, permissions | https://developers.facebook.com/docs/video-api/guides/reels-publishing (examples v27.0; one v18.0) | Matches sections 1–2 | DOCUMENTED |
| 2026-11-22 | Sidekick | Pages API token flow, tasks, App Review, Dev Mode | https://developers.facebook.com/docs/pages-api/overview | `/me/accounts` → page token; tasks table; all Page permissions need App Review for live | DOCUMENTED |
| 2026-11-22 | Sidekick | Post + comment permissions | https://developers.facebook.com/docs/pages-api/posts ; https://developers.facebook.com/documentation/pages-api/comments-mentions | `pages_manage_engagement`, `pages_manage_posts`, `pages_read_engagement`, `pages_read_user_content`; tasks `MODERATE`,`CREATE_CONTENT`; author = Page; error 1705 if commenting as user | DOCUMENTED |
| 2026-11-22 | Sidekick | Comment read edge | https://developers.facebook.com/docs/graph-api/reference/page-post/comments/ (v27.0) | filters, delayed read-after-write for video comments | DOCUMENTED |
| 2026-11-22 | Sidekick | Permissions requirements (Advanced Access, BV, 90-day regrant) | https://developers.facebook.com/docs/permissions/ | as noted; per-permission rows for `pages_*` not individually extracted from the page | DOCUMENTED (summary) |
| 2026-11-22 | Sidekick | Links in comments | https://developers.facebook.com/devpolicy/ ; community thread 10043996292385972 | no explicit API restriction found | UNVERIFIED |
| 2026-11-22 | Sidekick | Shopee Open API (TH) | https://affiliate.shopee.co.th/open_api and https://open-api.affiliate.shopee.co.th/explorer | JS-only/login-gated; content not readable | UNVERIFIED |
| 2026-11-22 | Sidekick | Shopee GraphQL shape | third-party mirrors only (addlivetag.com, affiliateshopee.com.br, github bcat95/shopee-aff; non-official, other regional hosts) | `productOfferV2`, `generateShortLink`, SHA256 `Authorization` header; region hosts differ (.vn/.com.br/.co.id; TH host assumed `open-api.affiliate.shopee.co.th`) | UNVERIFIED |
| 2026-11-22 | Sidekick | Mock publish spike | `spikes/phase0_publish` | Logic tested against a fake only | N/A (not provider evidence) |
| 2026-11-22 | Codex | Business Login and Page access | Local sanitized OAuth callback and Graph API v27.0 | Exactly one sandbox Page, all five requested Page permissions, and Page token identity verified | LIVE-VERIFIED |
