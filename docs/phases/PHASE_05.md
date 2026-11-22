# PHASE_05 — Bulk Campaigns & Automation

> Status: IN PROGRESS (local queue and 500 simulated jobs verified) | Owner: unassigned | Last reviewed: 2026-11-22
> Parent plan: `../ROADMAP.md` | Source of truth for this phase: this file

## Scope and boundaries

**In scope:** Campaigns, schedules, retries, reconciliation, pause/resume, observability.

**Prerequisites / dependencies:** Phase 4 provider status API and Phase 3 render queue.

**Out of scope:** Features assigned to future phases; premature provider integrations; unsupported Shopee Video affiliate basket automation.

**Required deliverables:** Campaign UI, job state machine, Celery workers and metrics.

**Exit gate:** 500 simulated jobs, no double publish, clear lifecycle and retries.

## Execution checklist (from master roadmap)

**Objective:** Core AffiFlowApp-style bulk workflow and job observability.

### Campaign UI
- [ ] Build Campaign Builder: choose products, videos, pages and timing.
- [x] Add campaign draft, review, approve, activate, pause, resume and cancel.
- [ ] Support target-specific captions and affiliate links.
- [ ] Build scheduling calendar and timezone-safe schedule editor.
- [ ] Support per-Page posting limits, cooldowns and conservative pacing.
- [x] Show total estimated jobs before activation.

### Execution engine
- [ ] Create `campaigns`, `campaign_items`, `publish_jobs`, `publish_attempts`, `post_comments`.
- [ ] Define explicit job state machine and legal transitions.
- [ ] Suggested states: DRAFT → VALIDATED → SCHEDULED → QUEUED → UPLOADING → PUBLISHING → VERIFYING → PUBLISHED → COMMENT_PENDING → COMPLETED.
- [ ] Handle FAILED, RETRY_WAITING, CANCELLED and NEEDS_ATTENTION.
- [x] Implement durable scheduler using database as the source of truth.
- [ ] Configure separate Celery queues: `render`, `publish`, `comment`, `reconcile`, `analytics`.
- [ ] Implement idempotency keys, uniqueness constraints and reconciliation checks.
- [ ] Retry transient failures with bounded exponential backoff and jitter.
- [x] Never automatically repeat an ambiguous publish without reconciling remote status.
- [ ] Implement dead-letter handling/manual retry for permanent failures.
- [ ] Support concurrency controls per tenant, Page and platform.
- [ ] Add status updates, searchable logs and progress counters.
- [x] Record remote published URL and comment result separately.

### Reliability/QA
- [ ] Test simulation: 100 products × 5 Pages = 500 jobs (not a claim of provider-permitted rate).
- [ ] Test worker restarts, network outages and delayed API responses.
- [x] Test pause/resume and schedule cancellation.
- [x] Verify no duplicate remote posts in timeout/retry test cases.
- [ ] Validate tenant/job access controls and user-visible failure recovery.

**Acceptance criteria:** Manage and observe a 500-job *staging workload*, with correct scheduling, error categorization and no unintentional duplicate publish under test. Live rates depend on Meta limits.

**Milestone:** Core MVP ready for controlled beta, subject to live API permissions and policy compliance.

## Verification and handoff

- [ ] Run relevant formatting, linting, type checks, unit tests and integration tests (or record why unavailable).
- [ ] Document commands and actual test output in `docs/agent/SESSION_HANDOFF.md`.
- [ ] Record API constraints, failed approaches, permission requirements and assumptions.
- [ ] Update this phase's checked tasks **only after evidence of completion**.
- [ ] Capture architectural decisions as short ADRs under `docs/decisions/`.
- [ ] Do not start implementation tasks in a later phase without an explicit decision.

## Notes / decisions

- The local Studio creates a campaign from completed renders and tracks its scheduled jobs. A separate database-backed worker handles simulation and can use the configured Facebook Page after live activation. The new queue completed 500 simulated jobs and verified all simulated Affiliate comments. The earlier provider test also reconciled 500 finish timeouts across five simulated Pages.
- Live scheduled campaigns, production Celery deployment, and multi-Page scheduling remain unverified or unfinished. The local worker stays in simulation mode by default.
