# Shopee Affiliate Studio

Local workflow for a single product from inventory and affiliate URL through MP4 preview and simulated Meta publishing. Start with [current phase](docs/agent/CURRENT_PHASE.md) and [roadmap](docs/ROADMAP.md).

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

## Check

```sh
uv run --project backend --extra test pytest backend/tests
npm run build --prefix apps/web
```

[API docs](http://127.0.0.1:8001/api/v1/docs) are available while the API runs. Meta OAuth remains a separate [feasibility spike](spikes/phase0_meta/README.md). The studio uses a local Meta test double and reconciles a simulated timeout before recording the final publishing state. Rendering runs on the local API process. Production workers, live Reel publication, and App Review remain outside this slice.
