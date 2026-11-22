# ADR-0004 — Product ingest MVP: manual + CSV; no scraping

- Date: 2026-11-22
- Status: Accepted
- Context: Shopee Open API eligibility and terms on image/data reuse are UNVERIFIED and BLOCKED on an account (API_FEASIBILITY B2, B3). CLAUDE.md forbids scraping restricted pages and session/token extraction.
- Decision: MVP ingest is manual entry and CSV import (name, source_url, price, image references, affiliate_url, tags). Each image carries a rights status. The affiliate URL is user-provided; `origin` records `user` or `shopee_api`. A Shopee Open API adapter is added only after approval and verified terms. A Chrome extension may follow, only for user-initiated capture of pages the user is permitted to use, with no cookie/token extraction.
- Alternatives considered: Scraping product pages (terms/legal risk); headless browser with user session (credential extraction, prohibited); third-party scraper services (same rights issue).
- Consequences: More manual work for users; lower legal risk; CSV template and validation needed; dedup on `(org_id, source_url)`.
- Verification / revisit trigger: Revisit when Shopee Open API access is granted and terms are read.
