# Current phase

- **Active:** Phase 5 local campaigns and publishing queue, building on the verified single-Reel flow.
- **Status:** Account and workspace, product import, FFmpeg preview, and Meta simulation are locally verified. Studio also passed one live Reel publication, Affiliate comment, and comment read-back.
- **Primary spec:** `../phases/PHASE_01.md`
- **Related specs:** `../phases/PHASE_02.md`, `../phases/PHASE_03.md`, `../phases/PHASE_04.md`
- **Phase 0 carry-over:** Live OAuth, Reel publication, and Affiliate comment posting and read-back passed on the test Page. Shopee Open API integration is paused. Operations are cataloged in `../api/SHOPEE_AFFILIATE_ENDPOINTS.md`.
- **Decision:** Verify the Studio connection by reading the existing Magiclean Reel, then test live writes with a new product after authorization.
- **Work branch:** `phase-00/feasibility`
- **Acceptance:** Studio published the Scotch-Brite Reel and verified its Affiliate comment via the live Meta API. See the session handoff for the result.
- **Phase 5 acceptance:** The durable queue completed 500 simulations. The Studio UI verified draft, activate, pause, resume and completion. Multi-Page and production worker deployment remain pending.

Edit this file when the active phase changes; keep it <30 lines.
