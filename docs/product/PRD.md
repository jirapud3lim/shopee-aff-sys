# Product Requirements Document — DRAFT

> Status: TO BE COMPLETED during Phase 0. Never treat draft fields as validated requirements.

## Problem & audience
- Intended users: Shopee affiliate creators managing authorized Facebook Pages.
- Problem: repetitive product import, video assembly, campaign scheduling, publishing status.

## MVP scope (Phases 0–5)
- Product ingest: manual, CSV, optional authorized extension.
- Affiliate URLs: user-provided and tracked with product origin.
- Video: image-based FFmpeg vertical MP4 templates.
- Publishing: Facebook Page Reels and permitted comments, only after approved API validation.
- Scheduling: batch jobs, retry/reconciliation, approvals, monitoring.

## Explicit exclusions
- Shopee Video third-party affiliate basket automation.
- Guaranteed approval for Meta/Shopee API access.
- Google AI video/Trends and other networks until future phases.

## Acceptance scenarios (expand into test cases)
1. Workspace A imports products and Workspace B cannot read them.
2. User renders a permitted product image set into a valid vertical MP4.
3. Authorized Page posting stores remote identifiers and reconciles uncertain outcomes.
4. Comment failure is visible independent of reel publish success.
5. Scheduled campaigns do not duplicate posts when jobs retry.

## Open decisions
- Target user segment and country, paid plans, allowed product ingestion routes.
- Meta permission path and review criteria for external customers.
- Asset usage, music licensing and affiliate disclosure requirements.
