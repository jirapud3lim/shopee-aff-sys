# Session handoff

## Phase 7 Google Trends (2026-11-22)

- Studio reads Thailand's official Google Trending Now RSS and shows 4- and 24-hour windows, freshness, approximate searches and Google Explore links. It matches Thai and Latin tokens against saved Shopee product names within the selected workspace. Manual keyword matching works independently of the feed.
- At 17:28 Bangkok time the live Studio API returned 10 Thai trends for 24 hours and 3 for 4 hours. The workspace had one Shopee product and no automatic match to that live snapshot. Searching `ผ้าไมโครไฟเบอร์` returned the saved Scotch-Brite cloth with the terms `ผ้า`, `ไมโคร` and `ไฟเบอร์`. An unrelated football query returned no matches.
- Chromium verified the live feed, time and keyword filters, the matching-only filter, and opening a saved product from manual search. `PYTHAINLP_READ_ONLY=1 PYTHAINLP_OFFLINE=1 backend/.venv/bin/python -m pytest backend/tests spikes/phase0_publish/tests -q` passed 34 tests with FFmpeg on PATH. The production web build and Alembic schema check passed.
- A controlled RSS fixture verified automatic matching to a relevant product, workspace isolation, and exclusion of products from other domains. A cache test verified the fallback during a feed outage.
- The feed has no category field. The production opportunity score and AI pipeline remain pending. Gemini, Veo and Shopee Open API remain deferred.

## Phase 6 staging operations (2026-11-22)

- Started the isolated Compose stack on Docker Desktop. PostgreSQL 17, the API, the web proxy, the campaign worker, and Prometheus were reachable. Existing Studio data and the staging secret were kept separate.
- The staging smoke test rendered an MP4, completed one simulated campaign, verified its simulated Affiliate comment, and received HTTP 403 for both live publish and live campaign creation. Prometheus reported a fresh worker heartbeat.
- Backup `20261122T101418201265971Z` passed the SHA-256 and isolated restore checks. The restored PostgreSQL database held one workspace, one render, and one campaign item. The completed MP4 was present. A restricted copy of the backup was exported under `backend/.local/staging-backups/`.
- Prometheus validated six rules and passed the stale-heartbeat test. It reported the backup timestamp after the API and worker restarted. The backend and publish-spike test suite passed 32 tests. The GitHub staging job was added and its checks were exercised locally.
- Billing and live staging writes remain off. Hosted deployment, automatic off-host backups, and external alert routing remain pending. See `docs/ops/STAGING.md`.

## Local campaign queue (2026-11-22)

- Phase 5 added campaign drafts, Bangkok scheduling, approval, pause, resume, cancellation, and job status in Studio. The separate worker persists jobs and its lease in the database. It reuses the existing Meta publication ledger when reading a requested post or comment.
- An isolated SQLite load test reopened a database session for each worker tick. The persisted results were 500 completed jobs, 500 verified simulated comments, and 0 live publications. The next tick found no due work. Browser verification created a draft, activated it, paused it, resumed it, and showed one completed simulation after a separate worker process ran.
- Backend and publish-spike tests passed (32). The web production build and the SQLite migration and Alembic schema check passed.
- Live campaigns are off by default. No live post or comment was made in this phase. The single-Page connection, production Celery deployment, and multi-Page scheduling have separate acceptance work.

## Shopee Affiliate CSV reporting (2026-11-22)

- Studio imports Click Report and Order Report CSVs into the selected workspace. The report groups clicks, unique orders, and commission by channel and Sub ID. Imported Sub IDs can match saved Studio links.
- Browser verification uploaded both fixtures into an isolated SQLite database. Import accepted 3 unique clicks from 4 rows and 5 order lines across 3 unique orders. The report showed ฿16.13 estimated and ฿6.00 confirmed. Filtering to Facebook and `fbcloth01-sale` showed ฿10.13 estimated and hid the TikTok row.
- The backend regression test covered repeat imports, an order status update, an older export, repeated order-level commission, invalid CSV rows, and workspace isolation. The production build, SQLite migration, and Alembic schema check passed.
- The connected Shopee account showed no rows for the checked periods and did not offer CSV downloads. The Studio workspace has no report rows. Shopee Open API remains paused.

## First live publication from Studio

- Enabled live posting in the local Studio for the configured workspace owner and the Page คัดของเข้าบ้าน.
- Created a Shopee Affiliate link for Scotch-Brite kitchen microfiber cloths (pack of two) with Facebook Sub ID `fbcloth01`. Studio rendered one 15-second Reel from three original graphics.
- The Studio interface submitted one public Reel and one Affiliate comment, then showed `published` and verified the Page-authored comment and Affiliate URL from Meta Graph API. The backend retained the publication and comment IDs. [Reel](https://www.facebook.com/reel/1974853066822019/) · [Verified comment](https://www.facebook.com/reel/1974853066822019/?comment_id=1793026762213749)
- Meta Graph API v27.0 returned Reel ID `1974853066822019` with `publish_status=published`. The comment creation response returned `1974853066822019_1793026762213749`; listing Reel comments returned `122097553173560732_1793026762213749` with the expected Page author, Affiliate URL and disclosure. Studio recorded `comment_verified=true`.

## Studio Meta connection

- Added workspace-owner access for one configured Facebook Page, publication state per render, and Reel and comment read-back. The Studio can post a Facebook-channel Affiliate comment once Meta confirms publication. The existing simulation remains usable.
- Verified the existing Magiclean Reel and its Affiliate comment from the Studio interface using Meta Graph API v27.0 with writes disabled. The Studio displayed the published status, Page author, Affiliate link and comment permalink.

## Earlier Affiliate results preview (2026-11-22)

- The original **ผลลัพธ์ Affiliate** view used 60 days of fixed demo data for clicks, orders and commissions. It supported date and channel filters, period comparisons, and performance by Sub ID. The two trends views used a fixed seven-day window with a Shopee ranking example and Studio order growth by product and channel.
- Adding a product from a card pre-fills its name in the existing product form. The user supplies the source URL. The browser keeps the sample-to-product association per workspace and uses it to reopen the saved product. Shopee reports and live rankings are pending the provider integration.
- Safari verification on an isolated SQLite database covered opening the report, switching to 30 days, switching to Studio order growth, and saving and reopening a product through a trend card.
- Browser verification on an isolated SQLite database also covered the Facebook channel filter, comparison toggle, valid and reversed custom date ranges, and reopening the saved trend product after reload. A second workspace showed its own product associations.
- ImageGen produced the three sample product photos in `apps/web/public/affiliate-demo/` using the built-in tool with this prompt.

  > Product mockup for a Thai affiliate dashboard. A single wide horizontal catalog contact sheet with exactly three equally sized side-by-side scenes, no gutters, each object centered in its own third with ample margin. Left: ivory compact portable handheld fan upright on light mint sage backdrop. Middle: dusty blue 750ml stainless steel insulated tumbler with handle and lid on soft powder blue backdrop. Right: cream modular drawer organizer tray containing two small neatly folded cloths on warm pale peach backdrop. Refined photographic ecommerce thumbnails with soft daylight, subtle shadows and believable materials, three isolated products, shot from eye-level slight three-quarter angle. No text, logos, hands, or watermark.

## First live Reel test (2026-11-22)

- Published one 15-second Magiclean test Reel using the Meta Graph API on คัดของเข้าบ้าน. The API reported `publish_status=published` and the user confirmed the Reel was visible. [Published Reel](https://www.facebook.com/reel/1474154981527533/)
- The original Magiclean publication and comment tests ran through direct Graph API calls before the Studio connection was implemented.
- The test caption and channel link are recorded in `drafts/fbkitchen01/`. The rendered previews and source photos are kept locally.
- Posted one Affiliate comment via Graph API v27.0 at `POST /1474154981527533/comments`. A direct GET by the returned comment ID and `GET /1474154981527533/comments` both confirmed the same author, message, and permalink. Meta returned `1474154981527533_1139470178465538` on creation and `122097541725560732_1139470178465538` when listing the Reel comments. The IDs share a comment suffix, while the prefixes are the video ID and post ID respectively. [Verified comment](https://www.facebook.com/reel/1474154981527533/?comment_id=1139470178465538)

## Phase verification follow-up

- Recorded Thai Shopee operations in `docs/api/SHOPEE_AFFILIATE_ENDPOINTS.md`. Account scope and authenticated calls remain unverified.
- Added GitHub Actions configuration for migrations, backend tests and web build. The hosted job has not run.
- Backend tests passed (13), including the 100-row CSV replay and workspace isolation check. Publish spike passed (15), including 500 simulated jobs with a finish timeout on every job and no duplicate Reels. Frontend type checking passed.


## Shopee Affiliate access (2026-11-22)

- The user decided to defer the Open API application because the account does not currently meet Shopee's criteria. No application was submitted.
- Shopee's Affiliate account is accessible and shows the Facebook Page คัดของเข้าบ้าน as verified. The Open API screen says the account does not have access. Shopee's application states more than 1,000 orders per month, a valid payout account, evidence of audience performance, and an operating plan among its criteria.
- Shopee's custom-link tool is available at https://affiliate.shopee.co.th/offer/custom_link. Use its generated link with manual product entry or CSV import. The dashboard requests payment and tax details.
- The local studio was started against a persistent SQLite database with FFmpeg on PATH. A real product and image-use permission are still needed.

## Local MVP slice (2026-11-22)

- The user chose to defer public publishing and build the single-product path across Phases 1–4 first. Three Luna medium agents implemented foundation, products and rendering. The main agent integrated migrations, a Next.js UI and the existing Meta test double, then reviewed and verified the system.
- The registered API covers authentication and workspaces, manual product entry/edit, CSV ingest, image-rights gating, three-image rendering and protected preview. Simulations record separate publish and comment states, reconcile a timeout without issuing a second finish request, and return the same result for an identical replay.
- The browser test used synthetic images and reached `published`, `posted`, and verified comment read-back in the local simulator. Local API verification also covered malformed CSV rows, duplicate source URLs and cross-workspace access. Alembic reached head and reported no schema drift on SQLite and PostgreSQL 17. PostgreSQL also rejected a cross-workspace foreign key, and the same product-to-simulation flow passed against PostgreSQL.
- The separate Meta OAuth spike confirmed via read-only Graph API that the existing token still identifies the renamed Page คัดของเข้าบ้าน. The studio has no live Meta publishing route. No Reel or comment was sent to Facebook.
- Verification: `uv run --project backend --extra test pytest backend/tests -q` with FFmpeg on PATH → 12 passed, including mixed JPEG/PNG/WebP input. Existing publish and OAuth spikes → 14 and 15 passed. `npm run build --prefix apps/web` and `npm run typecheck --prefix apps/web` passed.
- Run instructions are in `README.md`. Production workers, managed media storage, staged deployment, and a real Shopee product/affiliate link are still pending.

## Earlier feasibility work

## Current state
- Phase: 0 (in progress)
- Live Meta OAuth succeeded in Development Mode with Facebook Login for Business. The callback returned exactly one sandbox Page with `CREATE_CONTENT` and `MODERATE`, all five configured Page permissions, and no declined permissions.
- OAuth tokens are encrypted in the ignored `spikes/phase0_meta/.secrets/` directory. The sanitized callback receipt is in the ignored `spikes/phase0_meta/evidence/` directory.
- FFmpeg 9.0.2 rendered a synthetic 1080×1920, 30 fps, 15.000-second H.264/AAC video. Both Meta test suites passed locally (15 OAuth tests and 14 mock publishing tests).
- The live Reel publish, comment read-back, and Reel listing during processing remain pending. Shopee Affiliate TH Open API access and image/data reuse terms remain unverified.

## Live verification (2026-11-22)
- Meta permitted the loopback redirect automatically in Development Mode. The Business Login configuration uses a User access token and matches the five scopes in `.env.example`.
- The initial OAuth callback reached localhost but Python reported a TLS verification error. Starting the spike with `SSL_CERT_FILE=/etc/ssl/cert.pem` fixed certificate validation, and a fresh OAuth attempt succeeded.
- The Page token resolved to the sandbox Page via a read-only Graph API call. External publishing remains on hold until the single-product workflow has been reviewed and approved for a public test.

## Initial Phase 0 work (2026-11-22)
- Goal: Phase 0 documentation + local feasibility planning.
- Files changed: `docs/product/PRD.md`, `docs/api/API_FEASIBILITY.md`, `docs/architecture/SYSTEM.md`, `docs/architecture/ERD.md`, `docs/decisions/ADR-0001..0005`, `docs/backlog/PHASE_00_BACKLOG.md`, `docs/phases/PHASE_00.md`, `docs/agent/*`, `spikes/`, `.gitignore`.
- Commands/tests run and actual results: pytest as above → 14 passed; `bash -n spikes/phase0_video/render_sample.sh` → OK; render not executed (no ffmpeg).
- Decisions made: modular monolith + Celery; org_id + composite FKs, 404 on cross-tenant, RLS to evaluate in Phase 1; reconcile-before-retry with `unknown` / `failed_safe_to_retry` + settle window; ingest = manual + CSV; video = H.264/AAC 1080×1920 30 fps 15/20/30 s.
- Blockers / permissions needed: B1 Meta App + test Page + test user role; B2 Shopee Affiliate TH Open API access; B3 Shopee image/data reuse terms; B4 ffmpeg on dev machine; B5 Reel `video_id` as comment target unverified; B6 Meta doc inconsistencies (`finish` vs `complete`, `publish_video`).
- Open product assumptions to confirm with user: A1 Thailand market, A2 English UI first (Thai later), role matrix.

## Next action
Live Studio publication and comment read-back passed in the configured local workspace.
