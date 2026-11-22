# PHASE_01 — SaaS Foundation

> Status: IN PROGRESS (local account, workspace and database baseline verified) | Owner: unassigned | Last reviewed: 2026-11-22
> Parent plan: `../ROADMAP.md` | Source of truth for this phase: this file

## Scope and boundaries

**In scope:** Authentication, organizational tenant boundaries, environments and CI.

**Prerequisites / dependencies:** Phase 0 security and integration feasibility decisions.

**Out of scope:** Features assigned to future phases; premature provider integrations; unsupported Shopee Video affiliate basket automation.

**Required deliverables:** Migrations, authenticated UI, tenant tests, staging deployment.

**Exit gate:** Cross-tenant access fails reliably; CI and migrations repeatable.

## Execution checklist (from master roadmap)

**Objective:** Secure multi-tenant web app, API, persistence and deployment foundation.

### Frontend
- [ ] Create Next.js + TypeScript project and set up UI theme/tokens.
- [ ] Implement responsive app shell, sidebar, top bar and workspace switcher.
- [ ] Implement register, sign-in, sign-out and password reset.
- [ ] Implement profile and workspace settings screens.
- [ ] Implement consistent loading, empty, error and permission-denied states.
- [ ] Create sitemap/navigation placeholders for future modules.

### Backend/data
- [x] Bootstrap FastAPI with versioned API routes and OpenAPI docs.
- [ ] Add PostgreSQL, SQLAlchemy, Alembic and migration CI checks.
- [ ] Create `users`, `organizations`, `organization_members`, `sessions`, `audit_logs`.
- [ ] Implement session/security controls, password hashing and account verification.
- [ ] Implement organization lifecycle and workspace invitations.
- [ ] Implement role-based access controls on the server.
- [ ] Apply organization scoping to all tenant-owned tables and API queries.
- [ ] Add request validation, consistent error contracts and pagination.
- [ ] Add structured logs, correlation IDs and exception tracking.
- [ ] Set up Docker Compose for local dev; create staging deployment.
- [x] Add automated unit, integration and tenant-isolation tests.

**Acceptance criteria:** Users register/login, create/switch workspaces and cannot access another tenant's resources. Staging deploy and schema migrations are repeatable.

## Verification and handoff

- [ ] Run relevant formatting, linting, type checks, unit tests and integration tests (or record why unavailable).
- [ ] Document commands and actual test output in `docs/agent/SESSION_HANDOFF.md`.
- [ ] Record API constraints, failed approaches, permission requirements and assumptions.
- [ ] Update this phase's checked tasks **only after evidence of completion**.
- [ ] Capture architectural decisions as short ADRs under `docs/decisions/`.
- [ ] Do not start implementation tasks in a later phase without an explicit decision.

## Notes / decisions

- Local baseline implemented with a FastAPI API, SQLite and PostgreSQL migrations, Argon2 passwords, hashed session tokens, and tenant-scoped access. Staging, invitations, account verification and password reset are pending.
