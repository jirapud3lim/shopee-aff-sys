# Phase 0 / early Phase 1 backlog

Priority: P0 = blocks the exit gate or first slice; P1 = needed for slice A/B; P2 = later. Owners: U = user/account holder, A = agent.

| ID | Pri | Task | Owner | Acceptance test |
|---|---|---|---|---|
| P0-01 | P0 | Create Meta developer account, Meta App (Dev Mode), test Facebook Page; add test user role | U | App dashboard shows app in Development Mode; test user has Admin/task role on Page |
| P0-02 | P0 | Live OAuth prototype: login, request the 5 Page permissions, call `/me/accounts` | A+U | Log (no tokens) shows Page id/name list and granted scopes; token stored encrypted only |
| P0-03 | P0 | Install ffmpeg on an allowed machine; run `spikes/phase0_video/render_sample.sh` with 3 licensed images | U+A | Script prints `OK: 1080x1920, ~15s`; ffprobe shows h264/aac, 30 fps |
| P0-04 | P0 | Live Reel publish to the test Page with the rendered sample (start → upload → finish → status) | A+U | Page shows the Reel; `status.publishing_phase.publish_status=published` recorded in evidence log; confirm `finish` vs `complete` param |
| P0-05 | P0 | Live comment: post affiliate-link comment on the returned id and read it back | A+U | Comment visible on Page; GET comments returns it with `from` = Page; record whether Reel `video_id` works as target (B5) |
| P0-06 | P0 | Live ambiguity probe: list `video_reels` right after finish and during processing; check whether marker in description is matchable | A | Evidence log states whether processing/unpublished reels are listed and observed delay |
| P0-07 | P0 | Apply for Shopee Affiliate account and Open API credentials (TH); read terms on image/data reuse | U | Account approved or written blocker; terms summary added to API_FEASIBILITY (B2, B3) |
| P0-08 | P0 | Prepare 10+ test products with images, URLs, affiliate links, rights notes | U | CSV with ≥10 valid rows passes the import schema |
| P1-01 | P1 | Repo scaffold: `backend` (FastAPI, uv, pytest, ruff, mypy), `apps/web`, docker-compose Postgres/Redis, CI | A | `docker compose up` ok; CI runs lint, type check, tests green |
| P1-02 | P1 | Alembic baseline: users, organizations, organization_members, sessions with composite-FK conventions | A | Migration up/down works; test: child row with mismatched org_id is rejected by DB |
| P1-03 | P1 | Auth + `OrgContext` dependency; workspace create; membership check | A | Test: request with another org's id returns 404; non-member 404 |
| P1-04 | P1 | Two-org isolation test fixture and generic cross-tenant 404 test helper | A | Helper used by every resource endpoint test |
| P1-05 | P1 | RLS spike: app role + `SET LOCAL app.org_id` on one table | A | Test shows query without setting returns zero rows; update ADR-0002 status |
| P1-06 | P1 | Slice A: products CRUD + CSV import with dedup on `(org_id, source_url)` + affiliate link save | A | Import of file with duplicate URL creates one row and reports one skipped; workspace B cannot read |
| P1-07 | P1 | Port spike domain code into `backend/.../publishing/domain` with the same tests | A | Spike tests pass unchanged against the ported module |
| P1-08 | P1 | `publish_jobs` / `publish_attempts` tables with unique `idempotency_key`; attempts append-only | A | Inserting a second job with same key fails; UPDATE on attempts is denied |
| P1-09 | P1 | Slice B: FFmpeg render worker (Celery) + ffprobe validation + signed download | A | Rendered file passes spec checker; failed render surfaces error in `render_jobs` |
| P1-10 | P1 | Provider adapter `MetaReelsPort` with fake in CI; real adapter behind config flag | A | CI uses fake only; adapter unit tests with recorded sanitized fixtures (no tokens) |
| P1-11 | P1 | Token encryption service + log redaction test | A | Test greps logs/fixtures for token patterns, finds none |
| P2-01 | P2 | Reconcile scheduler (periodic task) and "Check status" endpoint | A | Unknown jobs older than window get reconciled in test with fake |
| P2-02 | P2 | Per-Page 30/24 h scheduler cap | A | Test: 31st item in a 24 h window is delayed |
| P2-03 | P2 | Meta App Review/Business Verification preparation (screencasts, privacy policy URL, data handling answers) | U+A | Submission checklist complete; timeline recorded |
| P2-04 | P2 | Chrome extension feasibility (permitted capture only) | A | Written decision whether it stays out of scope |
| P2-05 | P2 | Thai localisation plan | A | i18n framework chosen and documented |
