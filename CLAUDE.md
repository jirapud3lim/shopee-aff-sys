# CLAUDE.md — Affiliate Automation SaaS

## Mission
Build a secure multi-tenant SaaS. First deliver authorized **Shopee product/affiliate URL import → FFmpeg vertical video → Facebook Page Reels publishing → permitted affiliate comment → verifiable job status**. Future scope: Google Trends, Gemini/Veo, TikTok/Instagram/YouTube. Do NOT treat Shopee Video affiliate basket tagging as verified or in initial scope.

## Operating mode (follow every session)
1. Read `docs/agent/CURRENT_PHASE.md`, then **only** the corresponding `docs/phases/PHASE_XX.md`. Read `docs/ROADMAP.md` selectively when a dependency is unclear; do not load the full roadmap by default.
2. Inspect existing code and git status before edits; never overwrite unrelated changes.
3. State a small actionable plan and acceptance tests for the *current* task. Prefer a vertical slice over broad scaffolding.
4. Implement minimal coherent changes, run tests, and report actual outcomes. Do not claim work/tests/API access that did not occur.
5. Update phase checkboxes only after verified results. End session with concise `docs/agent/SESSION_HANDOFF.md` update.
6. If blocked by external accounts, secrets, App Review or missing permissions, produce a mock/test-double path, record the blocker, and ask for the **specific** missing item. Never attempt to bypass access controls.

## Stack and layout
- `apps/web`: Next.js + TypeScript + Tailwind + shadcn/ui
- `apps/extension`: Chrome Manifest V3, only when permitted
- `backend`: Python FastAPI, SQLAlchemy, Alembic, Pydantic
- PostgreSQL; Redis + Celery; FFmpeg; S3-compatible object storage; Docker
- Provider adapters: Meta, Shopee (if authorized), Google AI (later).
- Single repository, modular monolith, background workers; avoid premature microservices.
- `docs/ROADMAP.md` is reference; `docs/phases/PHASE_XX.md` controls current phase.

## Engineering rules
- Strict tenant isolation at the server/database query boundary; never trust organization IDs from a client without membership check.
- API and worker side effects must be idempotent; on ambiguous publish timeout **reconcile first**, do not blindly retry.
- Keep `video_publish_status` separate from `affiliate_comment_status`.
- Split pure domain logic from external I/O adapters; use test doubles in automated tests.
- Secrets/tokens must not appear in logs, prompts, commits or fixtures; encrypt provider tokens and support disconnect/revocation.
- Use typed code, migrations, validation, scoped authorization, structured logs, correlation IDs and meaningful tests.
- Keep user-visible messages clear and actionable, including partial failure.
- Preserve image rights, advertising disclosures, platform terms, official APIs, rate limits and user consent. Do not automate CAPTCHA bypass, scraping of restricted pages, or token/session extraction.
- Google Trends is interest data, not Shopee sales. Google Veo access and pricing must be verified before use.
- Do not mark platform-specific features as production-ready until confirmed with approved official integrations.

## Definition of Done for each task
- Requirement and acceptance condition met; scoped security checked.
- Applicable tests pass; commands and results stated truthfully.
- Schema/API/contracts updated where changed; docs/handoff updated.
- No exposed secrets or unverified external-service assumptions.

## First session
Open `docs/agent/CURRENT_PHASE.md` and `docs/phases/PHASE_00.md`. Begin with Phase 0 requirements + API feasibility **without claiming live API proof or creating production integrations**. Draft `docs/product/PRD.md`, `docs/api/API_FEASIBILITY.md` and architecture decisions; identify external setup blockers.
