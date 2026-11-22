# Current phase

- **Active:** Phase 6 operations. The isolated PostgreSQL staging stack, worker, backup/restore, and monitoring passed locally.
- **Status:** Account and workspace, product import, FFmpeg preview, and Meta simulation are locally verified. Studio also passed one live Reel publication, Affiliate comment, and comment read-back.
- **Primary spec:** `../phases/PHASE_01.md`
- **Related specs:** `../phases/PHASE_02.md`, `../phases/PHASE_03.md`, `../phases/PHASE_04.md`
- **Phase 0 carry-over:** Live OAuth, Reel publication, and Affiliate comment posting and read-back passed on the test Page. Shopee Open API integration is paused. Operations are cataloged in `../api/SHOPEE_AFFILIATE_ENDPOINTS.md`.
- **Decision:** Verify the Studio connection by reading the existing Magiclean Reel, then test live writes with a new product after authorization.
- **Work branch:** `phase-00/feasibility`
- **Acceptance:** Studio published the Scotch-Brite Reel and verified its Affiliate comment via the live Meta API. See the session handoff for the result.
- **Phase 5 acceptance:** The durable queue completed 500 simulations. The Studio UI verified draft, activate, pause, resume and completion. Multi-Page and production worker deployment remain pending.
- **Phase 6 acceptance:** Staging rejected live writes, processed one simulated publication, restored one PostgreSQL workspace and MP4 from backup, and scraped worker and backup metrics. Hosted deployment, off-host backup scheduling, and external alert routing remain pending. See `../ops/STAGING.md`.

Edit this file when the active phase changes; keep it <30 lines.
