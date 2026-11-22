# Prompt for Claude Code — Start Phase 0

Read `CLAUDE.md`, `docs/agent/CURRENT_PHASE.md`, and `docs/phases/PHASE_00.md`. Do not load the full roadmap unless needed. Inspect repository structure and `git status` first.

Complete Phase 0 **documentation and local feasibility planning only**:
1. Refine `docs/product/PRD.md` with specific actors, acceptance scenarios, in/out of scope and critical assumptions.
2. Refine `docs/api/API_FEASIBILITY.md` into a capability/permission matrix for official Meta Page OAuth, Reels publish/status, comments, Shopee permitted data import and affiliate links. Mark all untested claims clearly.
3. Refine `docs/architecture/SYSTEM.md` and `ERD.md` for modular-monolith design, tenant isolation, background job state machine and recovery from ambiguous network failures.
4. Create a prioritized small-task backlog with acceptance tests; identify exact account prerequisites for real API proof.
5. Do **not** fake API access, install paid services, request secrets in chat, or implement full Phase 1. If live credentials/approval are missing, use a documented mock proof-of-concept and record blockers.
6. Run any available validation, give actual results and update `docs/agent/SESSION_HANDOFF.md`. Only check off verified tasks.

Before coding, propose a short plan; after work, summarize changed files, verification and one next task.
