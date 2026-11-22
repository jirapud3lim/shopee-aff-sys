# PHASE_00 — Planning & API Feasibility

> Status: IN PROGRESS (docs done; live API proof blocked) | Owner: unassigned | Last reviewed: 2026-11-22
> Parent plan: `../ROADMAP.md` | Source of truth for this phase: this file

## Scope and boundaries

**In scope:** Meta OAuth + Page Reel + comment feasibility; Shopee import and asset rights.

**Prerequisites / dependencies:** API permissions and third-party rights; external review timelines cannot be guaranteed.

**Out of scope:** Features assigned to future phases; premature provider integrations; unsupported Shopee Video affiliate basket automation.

**Required deliverables:** PRD, SYSTEM, ERD, API_FEASIBILITY, capability matrix, decision log.

**Exit gate:** At least one authorized realistic E2E proof or documented blocker and fallback; no invented API support.

## Execution checklist (from master roadmap)

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
- [x] Write PRD: target users, use cases, supported channels, in/out of scope.
- [x] Define personas and roles: owner, admin, member.
- [x] Map full journey: import → affiliate URL → video → campaign → publish → comment → verify.
- [x] Define business events, failure behavior and user-facing status model.
- [x] Create architecture diagram, initial ERD and initial API contracts.
- [ ] Prototype Meta OAuth and retrieve authorized Pages.
- [ ] Test one real Page Reel publish through current official API.
- [ ] Test posting and reading an affiliate-link comment (where permitted).
- [ ] Test publishing idempotency/reconciliation behavior after ambiguous timeouts.
- [ ] Verify product capture/import path and optional Shopee API eligibility.
- [x] Define video spec: MP4, H.264, 1080×1920, vertical 9:16, template durations 15/20/30 s.
- [x] Record dependencies, costs, blockers and alternatives in an API feasibility report.

**Deliverables:** `docs/product/PRD.md`, `docs/architecture/SYSTEM.md`, `docs/architecture/ERD.md`, `docs/api/API_FEASIBILITY.md`, backlog, sitemap, wireframes.

**Acceptance criteria:** Feasible, authorized end-to-end paths are demonstrated or documented as blockers with fallbacks; no unsupported assumption is silently treated as solved.

## Verification and handoff

- [x] Run relevant formatting, linting, type checks, unit tests and integration tests (or record why unavailable).
- [x] Document commands and actual test output in `docs/agent/SESSION_HANDOFF.md`.
- [x] Record API constraints, failed approaches, permission requirements and assumptions.
- [ ] Update this phase's checked tasks **only after evidence of completion**.
- [x] Capture architectural decisions as short ADRs under `docs/decisions/`.
- [x] Do not start implementation tasks in a later phase without an explicit decision.

## Notes / decisions

- 2026-11-22: Docs drafted (PRD, SYSTEM, ERD, API_FEASIBILITY, ADR-0001..0005, `docs/backlog/PHASE_00_BACKLOG.md`).
- Idempotency/reconcile behaviour proven **against a fake only** (`spikes/phase0_publish`, 14 tests pass); the live checkbox stays open.
- Video spec defined (ADR-0005) but render NOT RUN: ffmpeg not installed (blocker B4).
- Exit gate status: no live E2E proof; blockers B1–B7 + fallbacks documented in API_FEASIBILITY §5.
