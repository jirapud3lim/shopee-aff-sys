# Shopee Affiliate Studio

Local workflow for a single product from inventory and affiliate URL through MP4 preview and Facebook publishing. Start with [current phase](docs/agent/CURRENT_PHASE.md) and [roadmap](docs/ROADMAP.md).

## Run locally

Install Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20.9+, and FFmpeg with both `ffmpeg` and `ffprobe` on `PATH`. Run these commands from the repository root.

```sh
uv sync --project backend --extra test
npm ci --prefix apps/web
export DATABASE_URL="sqlite:///$PWD/backend/local.db"
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

## Connect a local Facebook Page

Complete the [Meta OAuth spike](spikes/phase0_meta/README.md) for the Page and run the backend migrations. Set `META_TEST_PAGE_ID`, `META_STUDIO_WORKSPACE_ID` (from `GET /api/v1/workspaces` for the workspace owner), and optionally `META_STUDIO_PAGE_NAME` and `META_STUDIO_EXAMPLE_REEL_ID` in the root `.env`. With the same `DATABASE_URL` as the normal Studio, start the API using the saved encrypted Page token.

```sh
uv run --with cryptography python spikes/phase0_meta/run.py studio
```

Select **Facebook** in Studio and enter a Reel ID to read its publication status and the latest comments authored by the connected Page. Set `META_STUDIO_PUBLISH_ENABLED=true` and restart the API to make publishing available to the configured workspace owner. A completed render, a caption, and recorded image rights are required. Studio uses the Facebook channel's Affiliate URL for the optional comment, with the product's existing Affiliate URL as a fallback. After Meta confirms Reel publication, Studio posts the comment and polls for read-back. If processing outlasts polling or you close the page, load the same render and refresh its publication status to continue the pending comment. Each render can submit one live publication. Studio reconciles ambiguous responses by reading existing status.

## Check

```sh
uv run --project backend --extra test pytest backend/tests
npm run build --prefix apps/web
```

[API docs](http://127.0.0.1:8001/api/v1/docs) are available while the API runs. The simulation uses a local Meta test double and reconciles a simulated timeout before recording the result. Rendering runs on the local API process. Production workers and App Review remain outside this slice.
