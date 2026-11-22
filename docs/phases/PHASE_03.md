# PHASE_03 — Content Studio & Template Video Engine

> Status: NOT STARTED | Owner: unassigned | Last reviewed: 2026-11-22
> Parent plan: `../ROADMAP.md` | Source of truth for this phase: this file

## Scope and boundaries

**In scope:** Reels template pipeline using FFmpeg; preview, batch rendering, ownership of assets.

**Prerequisites / dependencies:** Phase 2 product images and access controls.

**Out of scope:** Features assigned to future phases; premature provider integrations; unsupported Shopee Video affiliate basket automation.

**Required deliverables:** Template editor, rendering workers, MP4 artifacts and render queue.

**Exit gate:** Batch render stress test, correct output specs, deterministic error reporting.

## Execution checklist (from master roadmap)

**Objective:** Convert product images into short vertical marketing videos at scale, without depending on paid AI video APIs.

### Video and content
- [ ] Define provider interface (`VideoProvider`) and request/result schema.
- [ ] Implement `FFmpegVideoProvider` as initial engine.
- [ ] Build template model: text layers, scenes, transitions, durations, themes, music.
- [ ] Create `video_templates`, `video_projects`, `video_scenes`, `video_assets`, `render_jobs`.
- [ ] Support product selection and batch generation.
- [ ] Validate and normalize input images before rendering.
- [ ] Implement vertical 9:16 MP4/H.264 export, configurable frame rate and resolution.
- [ ] Implement pan/zoom, fade/slide, overlays, title cards, price labels and CTA.
- [ ] Add licensed background-music selection and optional mute.
- [ ] Build browser preview, progress indicator and download action.
- [ ] Generate thumbnails, metadata and render artifact checksums.
- [ ] Add captions and hashtag editing; optional Gemini-generated text after API setup.
- [ ] Add render cancellation, retry, deduplication and error reporting.

### Worker/media infrastructure
- [ ] Configure Redis and separate Celery render queue/workers.
- [ ] Integrate object storage with signed URLs and retention policy.
- [ ] Track rendering time, CPU/RAM demand, storage size and unit cost.
- [ ] Put resource caps and concurrency limits on the rendering workers.
- [ ] Provide test fixtures for invalid images, long titles and broken fonts.
- [ ] Add quality/review step for factual product claims and licensed assets.

**Future compatibility:** `GoogleVeoProvider` is only an interface at this stage. Use official Cloud API later, not browser automation of Google Flow.

**Acceptance criteria:** Generate 100 valid vertical videos in a test batch with tracked statuses, retries, storage links and human review. Confirm capacity with actual infrastructure.

## Verification and handoff

- [ ] Run relevant formatting, linting, type checks, unit tests and integration tests (or record why unavailable).
- [ ] Document commands and actual test output in `docs/agent/SESSION_HANDOFF.md`.
- [ ] Record API constraints, failed approaches, permission requirements and assumptions.
- [ ] Update this phase's checked tasks **only after evidence of completion**.
- [ ] Capture architectural decisions as short ADRs under `docs/decisions/`.
- [ ] Do not start implementation tasks in a later phase without an explicit decision.

## Notes / decisions

- Pending.
