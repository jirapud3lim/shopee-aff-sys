# PHASE_06 — Billing & Production Readiness

> Status: NOT STARTED | Owner: unassigned | Last reviewed: 2026-11-22
> Parent plan: `../ROADMAP.md` | Source of truth for this phase: this file

## Scope and boundaries

**In scope:** Subscriptions, usage accounting, operations, compliance and public beta safety.

**Prerequisites / dependencies:** Core workflow stable; payment provider selection and legal policy review.

**Out of scope:** Features assigned to future phases; premature provider integrations; unsupported Shopee Video affiliate basket automation.

**Required deliverables:** Billing lifecycle, quotas, operations console, backup/restore runbook.

**Exit gate:** Payments/quotas tested across states; restored backups; beta-readiness signoff.

## Execution checklist (from master roadmap)

**Objective:** Enable multiple paying customers with transparent usage quotas, support and security.

### Plans and payments
- [ ] Define billable units: pages, videos rendered, publish jobs, AI credits, storage.
- [ ] Select payment provider with Thai payments/subscriptions/tax support.
- [ ] Create `subscriptions`, `plans`, `usage_events`, `payments`, `invoices` as needed.
- [ ] Implement trial and paid subscription lifecycles.
- [ ] Implement plan upgrade/downgrade/cancel and proration policy.
- [ ] Handle payment webhooks with signature verification and idempotency.
- [ ] Enforce usage quotas server-side using a ledger; not client-side counters.
- [ ] Add billing overview, invoices/payment history and warning notifications.

### Operations and compliance
- [ ] Build internal admin dashboard, tenant support and audit trails.
- [ ] Publish Terms, Privacy Policy, data deletion instructions and support contact.
- [ ] Review applicable PDPA/privacy, affiliate disclosures and provider policies.
- [ ] Configure production secrets, least-privilege IAM and key rotation.
- [ ] Add database backups, restore drills, storage retention and deletion policies.
- [ ] Add metrics/dashboards, alerting, incident runbooks and health checks.
- [ ] Add CI/CD with test gates, migration plan and rollback procedure.
- [ ] Conduct security review, abuse prevention and load tests.
- [ ] Prepare controlled beta/onboarding documentation.

**Illustrative, unvalidated pricing hypotheses (not market-verified):** Starter ฿299/mo (1 Page, 100 videos, 100 posts), Pro ฿799/mo (5 Pages, 500 videos, 1,000 posts), Business ฿1,990/mo (20 Pages, 2,000 videos, 5,000 posts). Validate unit economics and platform limits before using these prices.

**Acceptance criteria:** Customer signup → plan selection → payment → entitlement enforcement → cancellation works; security, support, backups and monitoring are production-ready.

## Verification and handoff

- [ ] Run relevant formatting, linting, type checks, unit tests and integration tests (or record why unavailable).
- [ ] Document commands and actual test output in `docs/agent/SESSION_HANDOFF.md`.
- [ ] Record API constraints, failed approaches, permission requirements and assumptions.
- [ ] Update this phase's checked tasks **only after evidence of completion**.
- [ ] Capture architectural decisions as short ADRs under `docs/decisions/`.
- [ ] Do not start implementation tasks in a later phase without an explicit decision.

## Notes / decisions

- Pending.
