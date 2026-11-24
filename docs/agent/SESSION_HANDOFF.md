# Session handoff

## Web features split (2026-11-24)

- Moved the 12 Studio components from `apps/web/app/` into `apps/web/features/{discovery,affiliate,production,publishing}/` and `safari-capture.ts` into `apps/web/lib/`. Imports now use an `@/*` alias added to `tsconfig.json`; `app/` keeps `page.tsx`, `layout.tsx`, `studio.css` and the API route. No behavior change. `StudioRequest` still lives in `publishing/meta-publishing.tsx` and should move to `lib/` in a later cleanup.
- Verified TypeScript, `next build`, and the Docker staging smoke (API release check, clean browser in all three Shopee modes, no-Computer-Use check). Not rerun: backup/restore drill and the launcher start.

## Backend package split (2026-11-24)

- Moved the 17 flat backend modules into `app/core`, `catalog`, `content`, `publishing` and `insights` with `git mv`, switched imports and monkeypatch strings to absolute `app.<package>.<module>` paths, and fixed the `__file__`-relative paths in `core/config.py` and `content/renders.py`. The worker command is now `python -m app.publishing.campaign_worker` in `compose.staging.yml`. No behavior change.
- Verified backend pytest (36 passed, 3 FFmpeg skips), SQLite Alembic upgrade, drift check and downgrade, imports sorted with ruff (77 pre-existing lint findings remain, down from 79), and the Docker staging smoke (API release check, clean browser and no-Computer-Use check; worker completed a job). Not rerun: backup/restore drill, Postgres migration. Web `features/` split is still deferred.

## Repository structure cleanup (2026-11-24)

- Committed the pending PRD-03 and no-Computer-Use work in two commits, then reorganized without behavior changes: `apps/safari-extension` is now `apps/extension`; the Master Prompt moved to `docs/product/prompts/`; the launcher moved to `scripts/open-studio.command` (root `Open Studio.command` is a thin wrapper for Finder); `sites/affiliate-studio` and `assets/facebook-page` moved under `marketing/`; `drafts/fbkitchen01` moved to `docs/evidence/`; older handoff entries moved to `docs/agent/archive/`. Links in README, AGENTS.md, CLAUDE.md, ignore files and the Computer Use check were updated.
- Added `STUDIO_DATA_DIR` (default `backend/.local`); `RENDER_ROOT` still overrides renders. Existing data was not moved, so older paths in the archive remain valid.
- Verified backend pytest (36 passed, 3 FFmpeg skips), web `tsc`, shell syntax and `git diff --check`. Not run: Docker staging smoke, `next build`, and an actual launcher start. `compose.staging.yml` stayed at the root because moving it changes build contexts. Backend package split (core/catalog/content/publishing/insights) and web `features/` split are deferred.

## Public Shopee extraction trial (2026-11-24)

- Parsed the accessibility tree in the user's already-open Safari window. It exposed 16 distinct Flash Sale cards with names, displayed prices and sales labels. These cards linked to the Flash Sale page and did not expose listing IDs or Affiliate commission.
- One direct, session-free public HTTPS request returned HTTP 200 with zero product listing anchors and no sample card name in the HTML. A clean session-free Chromium trial also returned HTTP 200 and exposed zero matching price rows or listing links in the observed window. This verifies one read from Safari's rendered page. Standalone extraction and Studio import remain unverified. No account or Affiliate data was changed.

## PRD-03 non-API partner link trial (2026-11-24)

- Reviewed Shopee Thailand's [partner link wrapping](https://help.shopee.co.th/portal/10/article/172214) and [Affiliate Portal batch link](https://help.shopee.co.th/portal/10/article/123906) instructions. Added opt-in partner URL generation with the workspace-scoped Affiliate ID and no Open API credentials. The first tracking slot holds the channel Sub ID. Available redirect evidence must match the listing, publisher and Sub ID.
- Verified the URL and tracking with fixtures, failed any attempted Open API call in the non-API endpoint test, and reached Storyboard in Chromium with the mocked partner response. Backend pytest passed 36 with three FFmpeg-dependent skips. TypeScript and diff checks passed. Account eligibility and attribution in the real Shopee Click Report remain unverified. No live link was generated.

## PRD-03 automatic Shopee Affiliate links (2026-11-24)

- Added a server-side Thai Shopee `generateShortLink` adapter gated to the configured workspace owner. Studio reuses saved links, supports one-click generation for a selected listing and Sub ID, and retains manual copy/paste. The setup checks known listing and tag mismatches, uses bounded allowlisted HTTPS HEAD redirects, and records operator review of saved channel links. Existing link APIs retain their response contracts.
- Verified the signed request, redirect limits, mismatch handling, link reuse and workspace isolation using fixtures. Backend pytest reported 30 passed and three FFmpeg-dependent skips. TypeScript, diff checks, and SQLite migration upgrade, downgrade and drift checks passed. Manual and mocked automatic UI workflows reached storyboard approval on the isolated production-mode Docker stack. PostgreSQL smoke and the Computer Use artifact, network and log checks passed.
- No App ID or Secret is configured locally. Live Thai Shopee API authorization, exact authenticated schema and link read-back remain pending. No credentials were exposed, and no live link or post was created.

## PRD-01 release check (2026-11-24)

- Built the production-mode web, API and worker containers on an internal Docker network. The artifact and service checks passed. Isolated Chromium saved a manual Affiliate link, imported a storyboard and approved a shot with zero Safari bridge or external browser requests. Safari Capture is disabled in the container web build and remains available in local development.
- The PostgreSQL smoke test passed link and storyboard checks, a 1080 × 1920 H.264 MP4 fixture import and full decode, a worker simulation with Affiliate comment read-back, live write guards, CSV attribution and deduplication, and worker metrics. Fixed PostgreSQL report import counts by using returned rows when psycopg reports an unknown rowcount. TypeScript and diff checks passed. Local backend pytest reported 22 passed with three FFmpeg-dependent skips.
- Added the fixture-only release checks to GitHub Actions. The local backup and restore drill, backup-age metric, Prometheus config and alert rules also passed with the isolated configuration. Hosted CI and live-provider verification remain pending. No live post or deployment was made.

## Production without Codex Computer Use (2026-11-24)

- Recorded the deployment constraint in AGENTS.md and linked the eight-stage [Computer Use audit](../product/COMPUTER_USE_AUDIT.md) and ten [open backlog tickets](../backlog/PRODUCTION_NO_COMPUTER_USE.md). The first production path uses operator handoffs and existing approved APIs. Google Cloud Veo Lite access, Flow character and Callirrhoe parity, Shopee API scopes, and TikTok Inbox Upload remain verification tasks. No runtime, provider access or publishing changes were made.

## Project status check (2026-11-24)

- Phase 7 remains active. Local HEAD and the cached upstream both pointed to `80811b0`, and the worktree was clean before this note. Ports 3014 and 8001 had no listeners. This check reviewed existing verification records and did not rerun the test suites.
- Reviewed the current Studio features in pipeline order against the workflow documentation and product workflow code. No runtime checks were repeated.
- Audited Codex Computer Use separately from Studio runtime integrations. Repository code uses Safari Capture, server APIs and FFmpeg without a Codex Computer Use dependency. Codex tool history confirms Computer Use for live Shopee offer and variant checks, Affiliate link creation, Flow stills and video, and source clip inspection. The reviewed records did not establish the exact UI tool for Facebook/TikTok upload or for Shopee report processing.

## A-100cm white Flow review (2026-11-24)

- Used the approved storyboard panels 01, 02 v2, 03 and 04 for the DoCoMall A-100cm white variant, Shopee Shop `393014471` / Item `44610002166`, with the saved presenter's Callirrhoe voice off-screen. Flow rejected combining an exact first-frame lock with the audio reference, then produced four clips from the approved image references with Veo 3.1 Lite at 9:16 for 40 credits.
- Downloaded and checked each 720 × 1280 source at approximately eight seconds. Shot 02 exposes the rod mount and starts its main narration around five seconds. Shot 03 adds an interior shelf and a row of boxes. Shot 04 changes some props. Checked frames and automated Thai transcription. Direct listening and the opening words of shot 01 remain unverified. All four originals were sent for separate review. Assembly and publication remain pending.
- Flow sources in shot order are [01](https://flow.google.com/project/81d65799-15e1-4834-b708-4e17857d09ff/edit/9bd01143-16e7-4fc9-be21-cc15ac2c54cf), [02](https://flow.google.com/project/81d65799-15e1-4834-b708-4e17857d09ff/edit/c75b538c-7b32-4dbd-a6f0-93e260f2201b), [03](https://flow.google.com/project/81d65799-15e1-4834-b708-4e17857d09ff/edit/afcdd0b9-0fcb-4102-9520-7a2219ca8360), and [04](https://flow.google.com/project/81d65799-15e1-4834-b708-4e17857d09ff/edit/93674de9-56e6-4a81-90c2-114b84969606).
- Commit verification passed TypeScript, launcher and Safari background syntax checks, and the staged diff check. Backend pytest passed 22 tests with three FFmpeg-dependent skips using a temporary Thai NLP data directory.

## Option A navigation and Storyboard prompt (2026-11-24)

- Grouped the existing Studio screens under Market, Affiliate links, Production, and Results. Kept the original hash routes for deep links and Safari Capture. The market shows the latest saved Storyboard when available.
- The first production step accepts and saves a creative prompt, and incorporates it into the still-image brief. Existing plans without the prompt field remain readable. No real Flow generation or publication was submitted.
- An isolated Studio browser test reached all 13 original views through the four menus, signed in with a fixture, reused its saved Affiliate link, saved the product-specific prompt, and loaded it in the still-only Flow brief. Webpack production build, TypeScript, and git diff checks passed. Backend pytest reported 22 passed and three FFmpeg-dependent skips.


## Market Affiliate autofill (2026-11-24)

- The market dialog now shows both saved Shopee URLs for the selected channel. When a link is missing and Safari Capture answers, selection starts its existing Shopee form handoff. The dialog retains the Affiliate route expected by the installed bridge while keeping the market behind it. Shopee still needs an explicit **เอา ลิงก์** click before returning a new link.
- Verified actual saved listing and Facebook link data in the running QA workspace. TypeScript, extension syntax, diff checks and a mocked extension handoff passed. Safari Settings showed no installed extension, and the user chose to leave it unloaded. No live new link was generated.


## Safari QA autofill (2026-11-24)

- The one-time review launch now fills the QA account even when Safari has already supplied a different saved login. Verified the correct QA email and a populated masked password in Safari. The sign-in form was left ready to submit.


## Option A production workflow (2026-11-24)

- Applied the selected market design to Studio’s signed-in UI and connected the Affiliate link dialog to all five pipeline steps. Existing and new links lead to the same product-scoped storyboard, still review, generation handoff, MP4 review and publishing preparation. The prior standalone tools remain accessible.
- The plan records its channel link. Shot approval is scoped to the displayed image version and workspace and records the reviewer and time. Editing the script creates a new plan with the existing reviewed references when the variant matches.
- Browser QA on separate ports covered existing and new link paths, draft save and revision, one-shot approval, video settings, MP4 review and publishing preparation. Inspected the dialog at desktop and 390 px. The launcher now defaults to the macOS CA bundle when SSL_CERT_FILE is unset. Verified the live Thailand feed returned 200 and matched a fixture offer. API checks covered wrong-channel plans, shot bounds, cross-workspace access and stale approval after image replacement. Next.js webpack build, typecheck and diff checks passed. Backend pytest passed 22 tests with three FFmpeg-dependent skips. Flow video generation and publication were not submitted.



Older entries: [archive](archive/SESSION_HANDOFF_2026-11-23_and_earlier.md).
