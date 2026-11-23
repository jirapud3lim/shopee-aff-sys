# PHASE_07 — Google Trends, Gemini & Veo

> Status: IN PROGRESS | Last reviewed: 2026-11-22
> Parent plan: `../ROADMAP.md` | Source of truth for this phase: this file

## Scope and boundaries

**In scope:** Trend discovery, Gemini scripts, Veo provider, human quality gate and AI cost controls.

**Prerequisites / dependencies:** Google Cloud billing/region/quotas and approved access; Phase 3 provider boundary.

**Out of scope:** Features assigned to future phases; premature provider integrations; unsupported Shopee Video affiliate basket automation.

**Required deliverables:** Trend matching, AI provider adapters, approval UI and cost ledgers.

**Exit gate:** AI pipeline works without fabricated product claims and enforces budget caps.

## Execution checklist (from master roadmap)

**Objective:** Discover trending demand, match relevant products, and generate AI-enhanced marketing videos.

### Google setup (do this now only if AI is needed earlier)
- [ ] Create Google Cloud project and billing account.
- [ ] Configure budget alerts, IAM, service identities and API secrets.
- [ ] Confirm available Gemini and Veo services, supported regions, model names, pricing and quotas.
- [ ] Apply for quotas/access if necessary; test a single low-cost API call first.
- [ ] Define approval and cost caps before running bulk generative jobs.

### Trends/product discovery
- [x] Validate ingestion from the official Google Trending Now Thailand RSS.
- [x] Build Trend Explorer for Thailand with 4- and 24-hour windows and keyword filters.
- [ ] Add category filtering when source category data is available.
- [x] Normalize Thai and Latin keywords and match them with saved Shopee products in the current workspace.
- [x] Rank products by trend volume, keyword relevance, and the last 30 Bangkok calendar days of attributable clicks and unique orders from Shopee CSVs. Show the component scores and underlying data.
- [x] Display source timestamp, freshness and approximate search volume.
- [x] Offer manual keyword lookup and let operators open a suggested product for review.
- [x] Open an editable Reel script from a ranked product and render a three-scene FFmpeg preview.

### AI content pipeline
- [ ] Implement optional Gemini text provider for captions/scripts/storyboards/prompts.
- [ ] Implement `GoogleVeoProvider` behind existing VideoProvider abstraction.
- [ ] Support image-to-video jobs asynchronously and handle polling/results/expiration.
- [ ] Use FFmpeg to stitch short generated shots into 15–30 s final ads.
- [ ] Add moderation, image fidelity checks, product claims verification and human approval.
- [ ] Track AI provider usage, costs, budget caps and plan-specific quotas.
- [ ] Provide template-video fallback on quota exhaustion, model failure or high cost.
- [ ] Add metrics for approved/rejected content and render cost per asset.

**Acceptance criteria:** Trend → relevant product → validated storyboard → AI/generated or template-based video → approved asset → campaign queue, with auditable cost tracking.

## Verification and handoff

- [ ] Run relevant formatting, linting, type checks, unit tests and integration tests (or record why unavailable).
- [ ] Document commands and actual test output in `docs/agent/SESSION_HANDOFF.md`.
- [ ] Record API constraints, failed approaches, permission requirements and assumptions.
- [ ] Update this phase's checked tasks **only after evidence of completion**.
- [ ] Capture architectural decisions as short ADRs under `docs/decisions/`.
- [ ] Do not start implementation tasks in a later phase without an explicit decision.

## Notes / decisions

- This slice uses the official Trending Now RSS for Thailand. The feed does not include categories. Matches use shared words in the local Shopee catalog and expose the matching terms.
- See [ADR-0006](../decisions/ADR-0006-thai-trend-discovery.md) for the feed and matching decisions.
- Gemini, Veo, and Shopee Open API are deferred. See the session handoff for verification of the Google Trends slice.
