# Session handoff

## Current state
- Phase: 0 (in progress)
- Implemented: Phase 0 docs; mock publish/comment spike (`spikes/phase0_publish`); ffmpeg sample script (`spikes/phase0_video`, not run)
- Verified tests: `uv run --with pytest pytest spikes/phase0_publish -q` → `14 passed` (fake Meta adapter only)
- External API approvals: none; nothing live-verified. Meta facts are DOCUMENTED (official docs, accessed 2026-11-22, Graph API v27.0); Shopee Open API UNVERIFIED (official docs login/JS-gated)

## This session (2026-11-22)
- Goal: Phase 0 documentation + local feasibility planning.
- Files changed: `docs/product/PRD.md`, `docs/api/API_FEASIBILITY.md`, `docs/architecture/SYSTEM.md`, `docs/architecture/ERD.md`, `docs/decisions/ADR-0001..0005`, `docs/backlog/PHASE_00_BACKLOG.md`, `docs/phases/PHASE_00.md`, `docs/agent/*`, `spikes/`, `.gitignore`.
- Commands/tests run and actual results: pytest as above → 14 passed; `bash -n spikes/phase0_video/render_sample.sh` → OK; render not executed (no ffmpeg).
- Decisions made: modular monolith + Celery; org_id + composite FKs, 404 on cross-tenant, RLS to evaluate in Phase 1; reconcile-before-retry with `unknown` / `failed_safe_to_retry` + settle window; ingest = manual + CSV; video = H.264/AAC 1080×1920 30 fps 15/20/30 s.
- Blockers / permissions needed: B1 Meta App + test Page + test user role; B2 Shopee Affiliate TH Open API access; B3 Shopee image/data reuse terms; B4 ffmpeg on dev machine; B5 Reel `video_id` as comment target unverified; B6 Meta doc inconsistencies (`finish` vs `complete`, `publish_video`).
- Open product assumptions to confirm with user: A1 Thailand market, A2 English UI first (Thai later), role matrix.

## Next action (one concrete task)
Install ffmpeg and run `spikes/phase0_video/render_sample.sh` (P0-03), then create Meta App + test Page (P0-01) for the live Reel proof.
