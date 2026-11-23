# Shopee Affiliate Studio

Local workflow for a single product from inventory and affiliate URL through MP4 preview, Facebook publishing, and manual TikTok publishing. Start with [current phase](docs/agent/CURRENT_PHASE.md) and [roadmap](docs/ROADMAP.md).

See the [project workflow diagram](docs/product/WORKFLOW.md) for the steps from product discovery to publication and Affiliate reporting.

## Run locally

Install Python 3.11+, [uv](https://docs.astral.sh/uv/), and Node.js 20.9+. Video rendering also needs FFmpeg with both `ffmpeg` and `ffprobe` on `PATH`.

On macOS, double-click [Open Studio.command](<Open Studio.command>) in Finder or run `./Open\ Studio.command` from the repository root. It starts the local API and opens [Studio in Safari](http://127.0.0.1:3014) when ready. Closing its Terminal window or pressing **Ctrl+C** stops both servers. When the local QA database and password file are available, the launcher opens that workspace and fills in the test email and password once. Click **เข้าสู่ระบบ** to sign in. Otherwise it uses `backend/local.db` and leaves the form ready for manual sign-in. Exporting `DATABASE_URL` selects a database for manual sign-in. Live publishing is disabled in the review session.

For manual startup, run these commands from the repository root.

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

The Studio navigation follows **เลือกเทรนด์ → คัดสินค้า → ลิงก์ Affiliate**. Choose a trend to prefill the Shopee keyword. Adjust that keyword, the minimum sales and the minimum commission, then choose an offer to open its link setup. Studio carries the selected trend and offer in the current browser tab, scoped to the workspace.

From link setup, open the selected offer in Shopee and paste its product URL into Studio. Copy it to Shopee's link tool with the chosen Sub ID, then paste the generated affiliate link back into the same Studio form and save it by channel. Studio reuses the existing catalog product if the listing is already saved. The saved links remain available under **ลิงก์ที่บันทึกไว้ทั้งหมด**.

Open **Google Trends** in Studio. Browse Thailand’s Trending Now RSS for the last 4 or 24 hours, filter by keyword, or show only trends with a product match. Studio highlights the matching words in saved Shopee product names from the current workspace. Select a match to open its inventory record.

Use **จับคู่คำค้นเอง** to check a phrase against the inventory and open it in Google Trends Explore. The Trending Now feed provides approximate search volumes and does not include a category field. The API caches the feed for 10 minutes and labels cached results when a refresh fails. The manual lookup uses the bundled Thai dictionary and works independently of the feed.

**อันดับโอกาสสินค้า** lists the top five distinct products for the selected trends. If a product matches several visible trends, its highest-scoring match is shown. The 100-point score combines estimated search volume (25), keyword overlap and a phrase bonus (35), imported clicks (15), and imported unique orders (25). Volume components scale logarithmically and cap at 100,000 searches, 100 clicks and 20 orders. Report history covers the last 30 calendar days including today in Bangkok time. The score uses reports linked to one saved product by Sub ID and channel, and excludes cancelled or unpaid orders. Missing data contributes zero points and is labelled separately from a recorded zero. Manual search shows relevance only.

Select **เตรียม Reel** on a ranked product, trend match, or manual match to open its video form with a three-scene script. Edit the on-screen text and assemble up to 12 product clips and photos with documented usage rights. For a photo-only preview, select 4–12 views. For video-only, supply at least 15 seconds of footage. Reorder the sources in Studio. It gives more screen time to motion where available and keeps the full source frame visible. Source audio is muted. Studio uses FFmpeg to burn the text into the 15-second preview and saves the MP4 under **ตัวอย่างที่บันทึกไว้**. The editable script stays in the current session. Captioned rendering requires FFmpeg with libass and a Thai font. Staging installs Noto Sans Thai, and macOS uses Sukhumvit Set.

For a planned edit, expand **ตัดตามแผน Master Prompt v2**, upload or paste the JSON, and order the media to match the displayed IDs `A1`–`A12`. The renderer uses a contiguous 15-second timeline, `REAL_PHOTO` or `REAL_VIDEO` sources, `cut` or `hold`, verified source time ranges for clips, and `subtitle_th` by shot. A plan with `ready_for_preview` or `review_required` can render. Use already prepared files for crop effects or B-roll. Empty the JSON field to use automatic timing.

## Preview a previously purchased product

Open **Reel จากสินค้าที่เคยซื้อ** and register a product after checking that the Shopee purchase was completed. Provide the product page, a direct Shopee image URL and two direct image URLs selected from search results on supported image hosts. Select the item and click **เก็บภาพและสร้างตัวอย่าง**. Studio downloads the three images, keeps the originals by source under `RENDER_ROOT/Asset/<workspace>/<product>/runs/<preview>`, and renders a private 15-second MP4. Each run uses a separate folder. These previews are kept separate from the publication workflow while image rights are being verified.

After the product preview has saved its photos, use **นำเข้าช็อตเปิดจาก Google Flow (MP4)** to upload a clip of up to 48 MiB and optionally add an opening caption. Studio uses up to the first four seconds, follows them with two saved product photos, and saves the 15-second preview and the source MP4 in the run folder. The composition is muted. The import requires a downloaded MP4 and uses no Google API.

Select **เปิดด้วยภาพสินค้าจริง แล้วแทรกช็อตจาก Flow** to start with a saved product photo. Studio places up to three seconds of Flow footage after four seconds of the real photo, then finishes with the remaining saved product photos.

For an operator-assisted collection run, the workspace API accepts the verified completed purchase and selected image sources at `POST /api/v1/workspaces/{workspace_id}/purchase-previews/collect-and-render`. It registers the product, collects the assets and builds its preview in one request. The completed run retains its own source manifest.

The local Safari extension in `apps/safari-extension` enables **ดึงจาก Safari และสร้างตัวอย่าง** when Studio is open at `http://127.0.0.1:3014/#purchase-previews`. Safari must already be signed in to Shopee and grant the extension access to Studio, Shopee and Google Search. The extension opens a temporary tab and looks for one completed household purchase with a recognizable model and three matching photos. Studio keeps its session token on the local page and uses it to submit the collected product and image URLs to the preview endpoint.

### Shopee product discovery

In Studio, open **สินค้าขายดีและค่าคอม**. It ranks the workspace's Shopee Affiliate offers using the sales count shown by Shopee and the displayed commission rate. The default filters are at least 100 units sold and 5% commission. The combined sort uses `log10(1 + displayed sales) × commission rate`. You can also sort by sales, commission rate, or estimated commission in THB per unit. A sales count with `+` is a lower bound. The amount in THB is an estimate based on the displayed price and rate.

The Studio home page shows product matches from Google Trends Thailand and saved Shopee offers in the current workspace. The Shopee shelf defaults to estimated baht per order. It uses the observed price multiplied by the observed commission rate. On mobile, **ไปที่สินค้าค่าคอมสูง** jumps straight to that shelf.

For refreshes, open [Shopee Affiliate Product Offers](https://affiliate.shopee.co.th/offer/product_offer) in Safari and search or pick a Shopee category. With Affiliate Studio Capture 0.4.0 enabled and access granted to that site and local Studio, click **ดึงข้อเสนอจาก Safari** on **คัดสินค้า Shopee**. Studio updates matching offer IDs and includes the product image when the offer card exposes a supported image URL. Existing offers remain selectable and can pick up images on refresh.

From **ตลาดสินค้า**, click **เลือกสินค้านี้**. Studio shows the product URL, saved Affiliate link, and Sub ID for the selected channel when available. If the default channel has no saved link and Safari Capture is enabled, Studio prepares the official Shopee custom link form with the exact listing URL and Sub ID. In Shopee, click **เอา ลิงก์** and Studio saves the returned link for the same listing and channel. The form also offers manual entry when the extension is unavailable. Open the source listing and the saved link to verify the product and channel before continuing.

The same dialog follows **เตรียม Storyboard → อนุมัติภาพนิ่ง → สร้างวิดีโอ → ตรวจพรีวิว → เผยแพร่**. It carries the verified product, variant, channel, Affiliate URL, and Sub ID. Still approvals apply to the displayed image version and selected shot numbers. A different image requires new approval. The video step lists the approved shots for manual Flow generation, and the preview step accepts a completed Studio render or finished MP4. The final step prepares the caption, disclosures, and media for the destination. Facebook simulation is available for saved Studio renders.

Studio groups the original tools in four main menus.

- **ตลาดสินค้า** contains the market and the contextual tools for Google Trends, Shopee offer import and ranking, and the product catalog.
- **ลิงก์ Affiliate** contains saved links, channel filters, and link setup.
- **งานผลิต** contains Storyboard, saved and rendered video, purchase previews, the campaign queue, publication simulation, and TikTok preparation.
- **ผลลัพธ์** contains Shopee CSV reporting and Facebook Reel publication and read-back.

Enter the creative prompt in the first step of the product workflow. Studio saves it with the plan and includes it in the still-image brief for Flow. Later steps retain the required image and video review gates.

### Prepare a still storyboard in Google Flow

1. Use the first of the [two prompts](Shopee_Studio_Reel_Master_Prompt_v2.md#2-สองพรอมต์ก่อนสร้างวิดีโอ) to analyze original images of the exact product variant and prepare separate reference stills. Check them against the originals.
2. Use **เตรียม Storyboard** beside a ranked Shopee offer or Google Trends match. Add the verified details and the reviewed product image or reference sheet, then save the shot plan. The Studio form also takes a presenter reference. Plans and images are stored under the workspace in `RENDER_ROOT/storyboards`.
3. For the Safari handoff, open Studio at `http://127.0.0.1:3014` with Affiliate Studio Capture 0.4.0 enabled. Sign in to Flow and give the extension access to local Studio and `flow.google.com`. Enter the Flow project or collection link once for the workspace, then click **สร้าง Storyboard ภาพนิ่งใน Flow**. Safari attaches both references and enters the prompt in Image mode at 9:16 with one output. If Flow waits for a direct click, click **เริ่มสร้าง** in the Flow tab once. Keep both tabs open while Studio checks for and loads the matching still for review.
4. For manual handoff, click **คัดลอกพรอมป์และเปิด Flow**, paste it and attach the references, then download and import the result. In either workflow, compare each photorealistic panel with the references before approval.


## Connect a local Facebook Page

Complete the [Meta OAuth spike](spikes/phase0_meta/README.md) for the Page and run the backend migrations. Set `META_TEST_PAGE_ID`, `META_STUDIO_WORKSPACE_ID` (from `GET /api/v1/workspaces` for the workspace owner), and optionally `META_STUDIO_PAGE_NAME` and `META_STUDIO_EXAMPLE_REEL_ID` in the root `.env`. With the same `DATABASE_URL` as the normal Studio, start the API using the saved encrypted Page token.

```sh
uv run --with cryptography python spikes/phase0_meta/run.py studio
```

Select **Facebook** in Studio and enter a Reel ID to read its publication status and the latest comments authored by the connected Page. Set `META_STUDIO_PUBLISH_ENABLED=true` and restart the API to make publishing available to the configured workspace owner. A completed render, a caption, and recorded image rights are required. Studio uses the Facebook channel's Affiliate URL for the optional comment, with the product's existing Affiliate URL as a fallback. After Meta confirms Reel publication, Studio posts the comment and polls for read-back. If processing outlasts polling or you close the page, load the same render and refresh its publication status to continue the pending comment. Each render can submit one live publication. Studio reconciles ambiguous responses by reading existing status.

## Prepare a TikTok post

Open **TikTok** in the Studio sidebar. Select a completed render under **วิดีโอ**, or open an already edited MP4 in the TikTok panel to preview it with its original audio. For a Studio render, download the MP4 from the panel.

Review the complete video and caption, describe any AI-generated visuals or audio, and include the commission disclosure for Affiliate content. Copy the caption and open TikTok Studio. Upload the reviewed file to the intended account, apply the applicable [AI label](https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content) and [commercial disclosure](https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service), and verify any product attachment against the selected product and variant. If a required control is missing in the web uploader, complete that step in the TikTok app before posting. Check the live post and any product attachment after publication.

This is a manual handoff. An API upload to the TikTok inbox requires a registered TikTok app with [Content Posting API approval and creator authorization for `video.upload`](https://developers.tiktok.com/docs/en/content-posting-api-get-started-upload-content).

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
