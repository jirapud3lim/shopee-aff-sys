# ERD — Phase 0 proposal (MVP entities)

Status: PROPOSED. Types are illustrative (PostgreSQL). Billing tables (`subscriptions`, `plans`, `payments`, `invoices`, `usage_events`) are **Phase 6** and omitted.

## Conventions
- Every tenant table has `org_id uuid NOT NULL` and `UNIQUE (org_id, id)`. Child tables reference parents with composite FKs `(org_id, parent_id) → parent(org_id, id)`, so a cross-tenant reference is impossible at DB level (ADR-0002).
- `users`, `organizations`, `plans` are global; everything else is tenant-owned.
- Timestamps are `timestamptz` UTC. Provider tokens are stored encrypted (`*_enc`), never in logs.

```mermaid
erDiagram
  organizations ||--o{ organization_members : has
  users ||--o{ organization_members : joins
  users ||--o{ sessions : has
  organizations ||--o{ platform_connections : owns
  platform_connections ||--o{ connected_pages : exposes
  organizations ||--o{ product_import_batches : runs
  product_import_batches ||--o{ products : creates
  organizations ||--o{ products : owns
  products ||--o{ product_images : has
  products ||--o{ affiliate_links : has
  products ||--o{ product_snapshots : versions
  video_templates ||--o{ video_projects : used_by
  products ||--o{ video_projects : source
  video_projects ||--o{ video_scenes : has
  video_projects ||--o{ render_jobs : renders
  render_jobs ||--o| video_assets : produces
  organizations ||--o{ campaigns : owns
  campaigns ||--o{ campaign_items : contains
  campaign_items }o--|| video_assets : uses
  campaign_items }o--|| connected_pages : targets
  campaign_items }o--|| affiliate_links : links
  campaign_items ||--o{ publish_jobs : publishes
  publish_jobs ||--o{ publish_attempts : logs
  publish_jobs ||--o{ post_comments : comments
  organizations ||--o{ audit_logs : records

  organizations { uuid id PK
    text name
    timestamptz created_at
    timestamptz deleted_at }
  users { uuid id PK
    text email UK
    text password_hash
    timestamptz created_at }
  organization_members { uuid id PK
    uuid org_id FK
    uuid user_id FK
    text role "owner|admin|member"
    text status "active|invited|removed" }
  sessions { uuid id PK
    uuid user_id FK
    uuid active_org_id "validated vs membership"
    text token_hash UK
    timestamptz expires_at }
  platform_connections { uuid id PK
    uuid org_id FK
    text provider "meta"
    text external_user_id
    bytea user_token_enc
    text status "active|expired|revoked"
    text scopes
    timestamptz token_expires_at }
  connected_pages { uuid id PK
    uuid org_id FK
    uuid connection_id FK
    text page_id
    text name
    bytea page_token_enc
    text tasks
    text status "active|needs_reconnect|disconnected" }
  product_import_batches { uuid id PK
    uuid org_id FK
    text source "manual|csv"
    int total
    int created
    int skipped
    text status }
  products { uuid id PK
    uuid org_id FK
    uuid batch_id FK
    text source_url
    text name
    bigint price_minor
    text currency
    text status "draft|ready|archived"
    text_array tags }
  product_images { uuid id PK
    uuid org_id FK
    uuid product_id FK
    text storage_key
    text rights_status "authorized|unknown|denied"
    text rights_note
    int position }
  affiliate_links { uuid id PK
    uuid org_id FK
    uuid product_id FK
    text url
    text origin "user|shopee_api"
    text sub_id
    text status "active|invalid" }
  product_snapshots { uuid id PK
    uuid org_id FK
    uuid product_id FK
    jsonb data
    timestamptz captured_at }
  video_templates { uuid id PK
    uuid org_id "null = system template"
    text name
    int duration_s "15|20|30"
    jsonb spec }
  video_projects { uuid id PK
    uuid org_id FK
    uuid product_id FK
    uuid template_id FK
    jsonb params
    text status }
  video_scenes { uuid id PK
    uuid org_id FK
    uuid project_id FK
    uuid image_id FK
    int position
    text overlay_text }
  render_jobs { uuid id PK
    uuid org_id FK
    uuid project_id FK
    text status "queued|rendering|ready|failed"
    text error
    timestamptz started_at
    timestamptz finished_at }
  video_assets { uuid id PK
    uuid org_id FK
    uuid render_job_id FK
    text storage_key
    int width
    int height
    int duration_ms
    text sha256
    bigint size_bytes }
  campaigns { uuid id PK
    uuid org_id FK
    text name
    text status "draft|awaiting_approval|approved|running|done|cancelled"
    bool require_approval
    uuid approved_by
    timestamptz approved_at }
  campaign_items { uuid id PK
    uuid org_id FK
    uuid campaign_id FK
    uuid product_id FK
    uuid video_asset_id FK
    uuid page_id FK
    uuid affiliate_link_id FK
    text caption
    bool post_comment
    timestamptz scheduled_at
    text status "draft|scheduled|running|done|partial|failed|cancelled" }
  publish_jobs { uuid id PK
    uuid org_id FK
    uuid campaign_item_id FK
    uuid page_id FK
    uuid video_asset_id FK
    text idempotency_key UK
    text marker
    text video_publish_status
    text remote_video_id
    text remote_url
    text affiliate_comment_status
    timestamptz ambiguous_at
    int version "optimistic lock" }
  publish_attempts { uuid id PK
    uuid org_id FK
    uuid publish_job_id FK
    int seq
    text phase "start|upload|finish|status|list|comment"
    text outcome "ok|definite_error|ambiguous"
    text correlation_id
    jsonb request_sanitized
    jsonb response_sanitized
    timestamptz created_at }
  post_comments { uuid id PK
    uuid org_id FK
    uuid publish_job_id FK
    text message
    text remote_comment_id
    text status
    text correlation_id }
  audit_logs { uuid id PK
    uuid org_id FK
    uuid actor_user_id
    text action
    text entity_type
    uuid entity_id
    jsonb meta
    timestamptz created_at }
```

## Constraints and indexes
| Table | Constraint / index | Purpose |
|---|---|---|
| all tenant tables | `NOT NULL org_id`, `UNIQUE (org_id, id)`, index `(org_id, created_at)` | isolation, listing |
| all child tables | composite FK `(org_id, parent_id)` → parent `(org_id, id)` | no cross-tenant link |
| organization_members | `UNIQUE (org_id, user_id)`; exactly one `owner` enforced in service + partial unique index | membership |
| platform_connections | `UNIQUE (org_id, provider, external_user_id)` | no duplicate connect |
| connected_pages | `UNIQUE (org_id, page_id)` | one row per Page per org |
| products | `UNIQUE (org_id, source_url)` (nullable URL → partial index where not null); optional `(org_id, lower(name))` non-unique | dedup on import |
| affiliate_links | partial `UNIQUE (org_id, product_id) WHERE status='active'` | one active link per product (MVP) |
| product_images | `UNIQUE (org_id, product_id, position)` | order |
| render_jobs | index `(org_id, status)` | worker pickup |
| campaign_items | `UNIQUE (org_id, campaign_id, product_id, page_id)`; index `(org_id, status, scheduled_at)` | no duplicate item, scheduler scan |
| publish_jobs | **`UNIQUE (idempotency_key)`**, `idempotency_key = sha256(org_id, campaign_item_id, page_id, video_asset_id)`; index `(org_id, video_publish_status)`; partial index where status = `unknown` | dedup, reconcile queue |
| publish_attempts | `UNIQUE (publish_job_id, seq)`; append-only (no UPDATE/DELETE grants) | immutable log |
| post_comments | `UNIQUE (publish_job_id, remote_comment_id)` where not null | no double record |
| audit_logs | index `(org_id, created_at)`; append-only | audit |

## Lifecycle state columns
- `render_jobs.status`, `campaigns.status`, `campaign_items.status`: see PRD §5.
- `publish_jobs.video_publish_status`: queued → starting → uploading → finishing → processing → published | failed; any ambiguous step → unknown → (reconcile only) → processing/published/failed/failed_safe_to_retry; failed_safe_to_retry → queued (new attempts, same job row, `remote_video_id` cleared; old id preserved in attempts).
- `publish_jobs.affiliate_comment_status`: not_requested | pending | posting | posted | failed | unknown | skipped (independent).
- Transitions are validated in the domain layer and guarded by `version` (optimistic lock).

## Phase 6 (not modeled)
subscriptions, plans, payments, invoices, usage_events.
