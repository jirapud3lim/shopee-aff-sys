# Shopee Affiliate Studio

Local workflow for a single product from inventory and affiliate URL through MP4 preview and Facebook publishing. Start with [current phase](docs/agent/CURRENT_PHASE.md) and [roadmap](docs/ROADMAP.md).

## Run locally

Install Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20.9+, and FFmpeg with both `ffmpeg` and `ffprobe` on `PATH`. Run these commands from the repository root.

```sh
uv sync --project backend --extra test
npm ci --prefix apps/web
export DATABASE_URL="sqlite:///$PWD/backend/local.db"
export PYTHAINLP_READ_ONLY=1 PYTHAINLP_OFFLINE=1
uv run --project backend alembic -c backend/alembic.ini upgrade head
uv run --project backend uvicorn --app-dir backend app.main:app --host 127.0.0.1 --port 8001
```

In a second terminal:

```sh
npm run dev --prefix apps/web -- --hostname 127.0.0.1 --port 3000
```

Open [Affiliate Studio](http://127.0.0.1:3000). Create an account, add a product or import a UTF-8 CSV, and enter a note documenting the rights to use its images. Render three still JPEG, PNG, or WebP images. Review the generated 15-second video and caption, then simulate publication. Adding a comment to the simulation requires an affiliate URL.

CSV columns. Set optional `affiliate_channel` and `affiliate_sub_id` to import the affiliate URL into a channel record. In Studio, select the product and open **ลิงก์ Affiliate ตามช่องทาง** to edit or copy a saved link. Shopee Open API work is paused.

```csv
name,source_url,affiliate_url,image_rights_note,affiliate_channel,affiliate_sub_id
```

PostgreSQL can be selected through `DATABASE_URL`. Run migrations before starting the API. The app saves local renders in `backend/.local/renders` or a directory set by `RENDER_ROOT`. The frontend proxies `/api/v1` to `http://127.0.0.1:8001` by default. Set `STUDIO_API_ORIGIN` before starting or building it to use a different API origin.

## Import Shopee Affiliate reports

Download the **Click Report** and **Order Report** from the Shopee Affiliate Portal. Open **ผลลัพธ์ Affiliate** in Studio and upload each CSV in its matching field. The click export needs Click ID and Click Time, and the order export needs Order ID and Order Time. Thai headers are supported. Keep any Channel, Referrer, Sub ID, item/model ID, order status, and commission columns from the export.

Studio deduplicates clicks by Click ID and upserts order lines by Order ID and item identity. When an order export includes an update timestamp, older records are skipped. For exports without update timestamps, import older files before newer files. Studio counts each order once and counts an order-level commission once, even when Shopee repeats it across item rows. Order status and available commission columns determine estimated and confirmed totals. The report dates use Bangkok time. A matching Sub ID can identify the channel and link the report to the saved Studio product. This workflow uses only the imported CSV files.

## Find Thai trends

Open **Google Trends** in Studio. Browse Thailand’s Trending Now RSS for the last 4 or 24 hours, filter by keyword, or show only trends with a product match. Studio highlights the matching words in saved Shopee product names from the current workspace. Select a match to open its inventory record.

Use **จับคู่คำค้นเอง** to check a phrase against the inventory and open it in Google Trends Explore. The Trending Now feed provides approximate search volumes and does not include a category field. The API caches the feed for 10 minutes and labels cached results when a refresh fails. The manual lookup uses the bundled Thai dictionary and works independently of the feed.

**อันดับโอกาสสินค้า** lists the top five distinct products for the selected trends. If a product matches several visible trends, its highest-scoring match is shown. The 100-point score combines estimated search volume (25), keyword overlap and a phrase bonus (35), imported clicks (15), and imported unique orders (25). Volume components scale logarithmically and cap at 100,000 searches, 100 clicks and 20 orders. Report history covers the last 30 calendar days including today in Bangkok time. The score uses reports linked to one saved product by Sub ID and channel, and excludes cancelled or unpaid orders. Missing data contributes zero points and is labelled separately from a recorded zero. Manual search shows relevance only.

## Shopee product discovery

In Studio, open **สินค้าขายดีและค่าคอม**. It ranks the workspace's Shopee Affiliate offers using the sales count shown by Shopee and the displayed commission rate. The default filters are at least 100 units sold and 5% commission. The combined sort uses `log10(1 + displayed sales) × commission rate`. You can also sort by sales, commission rate, or estimated commission in THB per unit. A sales count with `+` is a lower bound. The amount in THB is an estimate based on the displayed price and rate.

For refreshes, open [Shopee Affiliate Product Offers](https://affiliate.shopee.co.th/offer/product_offer) in Safari and search or pick a Shopee category. With Safari extension 0.2.0 and access granted to that page and local Studio, click **ดึงข้อเสนอจาก Safari**. It reads cards with all three values on the open results page. Studio updates matching offer IDs in the workspace. You can also enter details from an individual offer. Google Trends remains available from the ranking page.

## Connect a local Facebook Page

Complete the [Meta OAuth spike](spikes/phase0_meta/README.md) for the Page and run the backend migrations. Set `META_TEST_PAGE_ID`, `META_STUDIO_WORKSPACE_ID` (from `GET /api/v1/workspaces` for the workspace owner), and optionally `META_STUDIO_PAGE_NAME` and `META_STUDIO_EXAMPLE_REEL_ID` in the root `.env`. With the same `DATABASE_URL` as the normal Studio, start the API using the saved encrypted Page token.

```sh
uv run --with cryptography python spikes/phase0_meta/run.py studio
```

Select **Facebook** in Studio and enter a Reel ID to read its publication status and the latest comments authored by the connected Page. Set `META_STUDIO_PUBLISH_ENABLED=true` and restart the API to make publishing available to the configured workspace owner. A completed render, a caption, and recorded image rights are required. Studio uses the Facebook channel's Affiliate URL for the optional comment, with the product's existing Affiliate URL as a fallback. After Meta confirms Reel publication, Studio posts the comment and polls for read-back. If processing outlasts polling or you close the page, load the same render and refresh its publication status to continue the pending comment. Each render can submit one live publication. Studio reconciles ambiguous responses by reading existing status.

## Schedule publishing campaigns

Open **แคมเปญ**, add completed renders, review each caption and Bangkok posting time, then save and activate the draft. The worker uses the same `DATABASE_URL` and `RENDER_ROOT` as the API. Run it from the repository root after applying migrations.

```sh
PYTHONPATH=backend backend/.venv/bin/python -m app.campaign_worker
```

Simulation is the default. Pause prevents new submissions, and cancel removes queued work from execution. The worker continues to check results for requests already submitted. Use `--once` to process at most one due job. Live campaigns require both `CAMPAIGN_LIVE_ENABLED=true` and `META_STUDIO_PUBLISH_ENABLED=true` on the API and worker, the configured Facebook Page, and explicit activation by the workspace owner. With the encrypted OAuth token, run the live-capable worker using `uv run --with cryptography python spikes/phase0_meta/run.py worker`. The queue spaces live Reel submissions at least 10 minutes apart.

## Check

```sh
uv run --project backend --extra test pytest backend/tests
npm run build --prefix apps/web
```

[API docs](http://127.0.0.1:8001/api/v1/docs) are available while the API runs. The simulation uses a local Meta test double and reconciles a simulated timeout before recording the result. Rendering runs on the local API process. Production workers and App Review remain outside this slice.

For the isolated PostgreSQL staging stack, see [Staging operations](docs/ops/STAGING.md).
