# PHASE_08 — Multi-Platform & Scaling

> Status: NOT STARTED | Owner: unassigned | Last reviewed: 2026-11-22
> Parent plan: `../ROADMAP.md` | Source of truth for this phase: this file

## Scope and boundaries

**In scope:** Provider-specific TikTok/Instagram/YouTube; Shopee Video only after verified entitlement.

**Prerequisites / dependencies:** Permissions and App Reviews for each platform; provider abstraction.

**Out of scope:** Features assigned to future phases; premature provider integrations; unsupported Shopee Video affiliate basket automation.

**Required deliverables:** Capability matrix, provider integrations and cross-channel reporting.

**Exit gate:** A channel only shown as supported after live official-API validation.

## Execution checklist (from master roadmap)

**Objective:** Expand publishing without rewriting campaign semantics.

- [ ] Define `PublishingProvider` contract for auth, validate, upload, publish, status, capabilities and errors.
- [ ] Add Instagram Reels connector after account and permission validation.
- [ ] Add TikTok posting connector after approval and platform review.
- [ ] Add YouTube uploads/Shorts connector with OAuth and quota management.
- [ ] Add Pinterest publishing if relevant.
- [ ] Research Shopee Video Affiliate basket support separately; do not assume seller-video integrations meet this requirement.
- [ ] Add capability flags so UI only offers verified supported actions.
- [ ] Add cross-platform post analytics and source attribution where APIs permit.
- [ ] Add A/B testing for video/caption with compliant rate limits.
- [ ] Improve autoscaling, media CDN, worker capacity, caching and cost observability.
- [ ] Implement per-provider integration and contract tests.
- [ ] Explore conversion/sales analytics only from legitimately authorized attribution sources.

**Acceptance criteria:** New platform adapters deploy without changing core campaign/job architecture; unsupported capabilities are surfaced clearly to users.

## Verification and handoff

- [ ] Run relevant formatting, linting, type checks, unit tests and integration tests (or record why unavailable).
- [ ] Document commands and actual test output in `docs/agent/SESSION_HANDOFF.md`.
- [ ] Record API constraints, failed approaches, permission requirements and assumptions.
- [ ] Update this phase's checked tasks **only after evidence of completion**.
- [ ] Capture architectural decisions as short ADRs under `docs/decisions/`.
- [ ] Do not start implementation tasks in a later phase without an explicit decision.

## Notes / decisions

- Pending.
