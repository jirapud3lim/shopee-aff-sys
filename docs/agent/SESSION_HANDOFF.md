# Session handoff

## First live Reel test (2026-11-22)

- Published one 15-second Magiclean test Reel using the Meta Graph API on คัดของเข้าบ้าน. The API reported `publish_status=published` and the user confirmed the Reel was visible. [Published Reel](https://www.facebook.com/reel/1474154981527533/)
- The test ran outside Studio. Live comment posting and read-back remain unverified. The local Studio still simulates Meta publication.
- The test caption and channel link are recorded in `drafts/fbkitchen01/`. The rendered previews and source photos are kept locally.

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
Verify live comment read-back when a test comment is authorized.
