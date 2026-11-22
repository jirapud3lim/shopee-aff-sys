# PHASE_04 — Meta OAuth & Facebook Reels Publishing

> Status: NOT STARTED | Owner: unassigned | Last reviewed: 2026-11-22
> Parent plan: `../ROADMAP.md` | Source of truth for this phase: this file

## Scope and boundaries

**In scope:** Meta connection, authorized Facebook Page posting, status and comment verification.

**Prerequisites / dependencies:** Phase 0 live feasibility, Phase 3 sample video, Meta permissions.

**Out of scope:** Features assigned to future phases; premature provider integrations; unsupported Shopee Video affiliate basket automation.

**Required deliverables:** Meta adapter, encrypted tokens, post verification and failures.

**Exit gate:** Live approved Page workflow verified; ambiguous timeout cannot double-post.

## Execution checklist (from master roadmap)

**Objective:** Authorized Page connections and reliable publishing to Facebook Reels.

### Account connection
- [ ] Configure Meta App, redirect URLs, data-use/privacy pages and webhook/security settings as appropriate.
- [ ] Implement OAuth flow with CSRF/state validation.
- [ ] Request and validate the minimum current API permissions needed.
- [ ] List and select Pages accessible to the connected user.
- [ ] Store credentials encrypted; track scopes, expiry, revocation and reconnect needs.
- [ ] Implement connect/disconnect and permission-health dashboard.
- [ ] Prepare Meta App Review evidence and business verification if applicable.

### Reels and comments
- [ ] Implement current official upload/start/finalize flow for Page Reels.
- [ ] Validate video constraints and caption before sending.
- [ ] Save remote IDs, post URL, provider responses and sanitized errors.
- [ ] Implement publish-status polling/reconciliation.
- [ ] Add optional affiliate-link comment workflow if permitted by scopes/policies.
- [ ] Track video publish and comment post statuses independently.
- [ ] Prevent blind retries when timeout leaves unknown remote state.
- [ ] Handle token failures, rate limits, permission changes and media rejection.
- [ ] Add disconnect/revoke flow and appropriate retention/deletion behavior.

**Acceptance criteria:** With approved test access, connect Page → upload Reel → verify published URL → post/verify comment (if approved) → capture status and failure details. Document restrictions for public users.

## Verification and handoff

- [ ] Run relevant formatting, linting, type checks, unit tests and integration tests (or record why unavailable).
- [ ] Document commands and actual test output in `docs/agent/SESSION_HANDOFF.md`.
- [ ] Record API constraints, failed approaches, permission requirements and assumptions.
- [ ] Update this phase's checked tasks **only after evidence of completion**.
- [ ] Capture architectural decisions as short ADRs under `docs/decisions/`.
- [ ] Do not start implementation tasks in a later phase without an explicit decision.

## Notes / decisions

- Pending.
