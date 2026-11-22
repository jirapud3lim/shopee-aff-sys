# ADR-0002 — Tenant isolation at the database and query boundary

- Date: 2026-11-22
- Status: Accepted (application + FK layers); Proposed (Postgres RLS layer)
- Context: Multi-tenant SaaS holding provider tokens and customer media; a cross-tenant leak is the highest-severity bug.
- Decision: Every tenant-owned table has non-null `org_id` and `UNIQUE (org_id, id)`. Child tables use composite FKs `(org_id, parent_id)` so cross-tenant references are impossible. The server resolves the org from the authenticated membership and never trusts a client org id without a membership check. All repository methods require an `OrgContext`. Cross-tenant access returns 404, not 403. Postgres RLS (`SET LOCAL app.org_id`) is defense in depth to be evaluated in Phase 1.
- Alternatives considered: Schema-per-tenant (migration and pooling cost); DB-per-tenant (cost); app-level filtering only (single bug leaks data); RLS only (hard to test, easy to bypass with a superuser role).
- Consequences: Slightly more verbose schema and queries; tests need a two-org fixture; workers must build an `OrgContext`; RLS needs a non-superuser app role and per-transaction setting.
- Verification / revisit trigger: Cross-tenant 404 test for every endpoint; DB test that inserting a mismatched `org_id` child fails; Phase 1 RLS spike decides the final layer.
