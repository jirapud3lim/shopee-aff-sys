# PHASE_02 — Product Collector & Affiliate Library

> Status: IN PROGRESS (manual and CSV product flows verified) | Owner: unassigned | Last reviewed: 2026-11-22
> Parent plan: `../ROADMAP.md` | Source of truth for this phase: this file

## Scope and boundaries

**In scope:** Manual/CSV product ingest and affiliate-link management; extension as verified add-on.

**Prerequisites / dependencies:** Phase 1 authorization and storage; Shopee terms review.

**Out of scope:** Features assigned to future phases; premature provider integrations; unsupported Shopee Video affiliate basket automation.

**Required deliverables:** Product library, CSV preview/errors, dedup, provenance, extension prototype.

**Exit gate:** 100-row import, isolation and rollback/error handling verified.

## Execution checklist (from master roadmap)

**Objective:** Reliable data ingestion and product inventory for downstream content creation.

### Product management
- [x] Implement manual product entry/edit and validation.
- [ ] Create `products`, `product_images`, `affiliate_links`, `product_import_batches`, `product_snapshots`.
- [ ] Build product grid/table view with filter, search, sort, pagination and tags.
- [ ] Support source URL, affiliate URL, product name, price/currency, category and multiple images.
- [ ] Store original and last-verified values separately to avoid stale-price claims.
- [ ] Add product image thumbnails and gallery.
- [ ] Implement duplicate detection and merge/update decisions.
- [ ] Add bulk select/edit/archive/export operations.
- [ ] Add product readiness/completeness indicators for video generation.

### Import and extension
- [ ] Implement CSV/Excel sample templates and mapping UI.
- [ ] Validate rows, preview errors, report duplicates and show import summary.
- [ ] Support import retry and downloadable error reports.
- [ ] Design Chrome MV3 extension (minimum permissions).
- [ ] Capture only authorized product information; send securely to backend API.
- [ ] Validate extension behavior against website terms; do not bypass CAPTCHA/auth controls.
- [x] Keep manual input and CSV as primary fallbacks for unsupported sources.
- [ ] Optionally integrate an authorized Shopee affiliate API only after approval.

**Acceptance criteria:** Import 100 test products reliably, detect duplicates, retain affiliate links, and enforce tenant isolation.

## Verification and handoff

- [ ] Run relevant formatting, linting, type checks, unit tests and integration tests (or record why unavailable).
- [ ] Document commands and actual test output in `docs/agent/SESSION_HANDOFF.md`.
- [ ] Record API constraints, failed approaches, permission requirements and assumptions.
- [ ] Update this phase's checked tasks **only after evidence of completion**.
- [ ] Capture architectural decisions as short ADRs under `docs/decisions/`.
- [ ] Do not start implementation tasks in a later phase without an explicit decision.

## Notes / decisions

- The local slice supports manual entry and editing, CSV import, duplicate and error reporting, user-supplied affiliate URLs and notes on image rights. Live Shopee API execution is pending. The 100-row CSV acceptance test passed, including duplicate detection on replay and isolation across workspaces.
