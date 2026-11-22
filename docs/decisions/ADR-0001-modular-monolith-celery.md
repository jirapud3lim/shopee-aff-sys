# ADR-0001 — Modular monolith with Celery workers

- Date: 2026-11-22
- Status: Accepted (proposal for Phase 1 confirmation)
- Context: Small team, one deployable preferred, but render and publish work is slow, retried and rate-limited. CLAUDE.md forbids premature microservices.
- Decision: One FastAPI codebase organised in modules (identity_tenancy, catalog, affiliate, media_render, campaigns, publishing, provider_adapters, audit) with pure domain code separated from adapters. One PostgreSQL. Celery + Redis for render, publish and reconcile tasks; tasks carry ids and `org_id`, load state from the DB, and are idempotent.
- Alternatives considered: Microservices (operational cost, no need); in-process background tasks only (lost on restart, no retries); DB-polling workers without a broker (workable, weaker tooling); Temporal-style workflow engine (powerful but heavy for MVP).
- Consequences: Simple deploys and transactions; module boundaries enforced by convention and import-lint; Redis is an additional dependency; broker loss must not lose jobs, so the DB is the source of truth and a scheduler re-enqueues due work.
- Verification / revisit trigger: Phase 1 skeleton with import-lint test; revisit if render throughput or team size requires service extraction.
