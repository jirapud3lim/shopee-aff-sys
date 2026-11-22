# Architecture — PROPOSED

Next.js UI and Chrome Extension (future) → FastAPI modular monolith → PostgreSQL.
FastAPI schedules render/publish jobs through Redis + Celery workers.
Object storage holds user-authorized product images and rendered MP4 files.
Meta/Shopee/Google integrations remain behind provider interfaces with mocks.

## Invariants
- Every tenant-owned row is org-scoped and verified server-side.
- External publish attempts have idempotency keys and remote identity reconciliation.
- Video publish and comment are independent operations/states.
- API credentials are encrypted at rest, never printed or committed.

## TBD Phase 0
- C4 diagrams, component responsibilities, ERD, API boundaries, job transition rules and threat model.
