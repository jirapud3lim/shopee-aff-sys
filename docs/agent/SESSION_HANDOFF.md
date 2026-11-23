# Session handoff

## Project workflow and TikTok handoff checkpoint (2026-11-23)

- Documented verified product identity, Flow storyboard approval, MP4 review, platform disclosures, Facebook and TikTok publication paths, and Shopee Affiliate reporting in `docs/product/WORKFLOW.md`.
- The Next.js webpack build and Meta publishing regression test passed. The information site source remains local because it includes the contact approved for the private Privacy Policy page and public access remains pending.

## Affiliate Studio information site for TikTok Sandbox (2026-11-23)

- Prepared a static product page, Terms of Service and Privacy Policy under `sites/affiliate-studio`. Included the operator and privacy contact supplied by the user in the Privacy Policy. Checked the home page and policy links locally, then deployed version 1 with owner-only access.
- Exported the existing Affiliate Studio mark as a 1024 × 1024 PNG and uploaded it to the TikTok Sandbox form. The form dropped from four validation errors to three. Automatic review rejected switching the website to public because the request did not explicitly approve public access to all three pages. TikTok cannot verify the URLs until that access is approved.

## TikTok developer Sandbox setup (2026-11-23)

- Created the Individual developer app **Affiliate Studio** and its **Inbox Upload Test** Sandbox. In the Sandbox editor, added Login Kit and Content Posting API, confirmed the listed `video.upload` scope, and entered the Desktop OAuth callback `http://127.0.0.1:8046/callback/`. Direct Post is off.
- TikTok requires the app's official website, Terms of Service, and Privacy Policy URLs before applying the configuration. The browser holds the unsaved form. Target-user authorization and the API upload test remain pending.

## TikTok Content Posting API readiness (2026-11-23)

- Studio has no TikTok OAuth or Content Posting API configuration. The Manage Apps portal in Safari displayed a separate TikTok for Developers sign-in, so app and scope approval remain unverified. The previous web upload did not use the API.
- The next live check is an authorized `video.upload` file upload confirmed by `SEND_TO_USER_INBOX` and the matching inbox notification. TikTok documents Sandbox for restricted testing with a target user and URL verification for Content Posting API. No API upload was attempted.

## TikTok Studio live upload test (2026-11-23)

- After signing in to the intended account in Safari, uploaded a non-product test pattern directly through the TikTok Studio web uploader. The 15-second 720 × 1280 MP4 with H.264 and AAC passed a full local decode. TikTok showed **Uploaded (6.28 MB)** and a 15-second preview. Left the composer open before publication. No post was published.

## TikTok publishing handoff (2026-11-23)

- Added a TikTok destination to Studio. It previews the selected completed Reel or a finished local MP4, downloads the Studio render, and copies the caption with optional AI and Affiliate disclosure text. The upload link opens TikTok Studio for account selection, platform disclosures, and manual publishing.
- Verified the completed-render preview and download link, copy and paste of both disclosures, and local MP4 selection and removal in Safari against an isolated fixture. Switching to the local file cleared the previous caption and disclosures. The Next.js webpack build, Meta publishing regression test, and `git diff --check` passed.
- No TikTok account was connected, and no clip was uploaded or published to TikTok. API draft upload requires an approved TikTok app and creator authorization for `video.upload`.

## Consolidated Studio updates (2026-11-23)

- Before committing the two-step storyboard prompts, shared production rules, and Facebook Reel product-tag handoff, reran the Next.js webpack build, the Meta publishing regression test, and `git diff --check`. All passed.

## Facebook desktop Reel product-link draft test (2026-11-23)

- With user approval, uploaded the original 15-second Scotch-Brite test render to คัดของเข้าบ้าน in Safari. The new Reel composer displayed Settings → Add product → Add product link. The saved Facebook-channel Shopee Affiliate short URL still resolved to the exact two-pack listing in Safari, but the Facebook form reported an invalid URL and did not attach it. The canonical listing URL failed the approved-domain check. The signed-in [Meta Help Center](https://www.facebook.com/business/help/1947397312436633) documents a linked partner account and a single-product link, and excludes shortened URLs for automatic banner detection. The partner catalog path remains unverified.
- Enabled the AI label and saved the Reel as a draft without a product tag. Confirmed the draft appeared in Content Library → Drafts and no new item appeared in Published. No publish command was sent.

## Facebook Affiliate setup read-back (2026-11-23)

- After the user completed mobile setup, Safari showed Affiliate Partnerships under Your Programs for คัดของเข้าบ้าน, previously under Ready to set up. The desktop program tile was disabled, so it did not identify the connected partner. The existing Scotch-Brite Reel's desktop post edit screen had no product-link control. The new Reel composer required a video before advancing. No video was uploaded, no changes were saved, and no post was published.

## Facebook Reel product-tag handoff (2026-11-23)

- Added a publishing mode for native Shopee product tags. Studio prepares the selected render, caption with commission disclosure, and the product's Facebook Affiliate URL or Shopee listing URL. The operator opens the configured Page and completes the product tag and applicable disclosures in Facebook before sharing. The Meta API publishing and Affiliate comment path remains available.
- Verified in Safari against an isolated two-product fixture that the caption and product URL copy, the MP4 download matches its source byte for byte, switching products clears the previous clip and URL, and switching back exposes the existing publishing controls. The fixture received no publishing write. Live banner verification still requires completing the Page's Affiliate Partnerships setup on mobile.

## Facebook Page Affiliate setup check (2026-11-23)

- Switched to the คัดของเข้าบ้าน Page in Safari. Creator Dashboard → Monetization showed Affiliate Partnerships under Ready to set up. Opening it redirected to a QR setup page requiring the Facebook mobile app to connect the Affiliate account. Left the setup page open. Account linking and the native Add product links control on a Reel remain unverified. No accounts were linked and no Reel was published.

## Facebook Reel product tagging check (2026-11-23)

- Checked the live publishing UI and Meta adapter. Studio publishes the Reel and optionally posts and verifies an Affiliate URL in a Page comment. It has no native product-tag input, write, or read-back. The public [Page Video Reels API v27.0](https://developers.facebook.com/docs/graph-api/reference/page/video_reels) lists no product-tag field. [Shopee Thailand](https://help.shopee.co.th/portal/10/article/185398) documents the native product banner through Facebook Affiliate Partnerships for eligible Pages. The configured Page's Partnership eligibility and native banner remain unverified. No live post was made.

## AI content and disclosure rules (2026-11-23)

- Added project-wide rules for separate AI and Affiliate disclosures, verifiable claims and asset rights, and channel-specific checks for TikTok, Meta Reels, and Mission Shopee Video. Linked the rules from the publishing step, CLAUDE.md, and Reel Master Prompt. Verified the documentation with `git diff --check`.

## Shared product pipeline rules (2026-11-23)

- Added one set of rules in AGENTS.md for every product and linked it from CLAUDE.md and the Reel Master Prompt. The rules cover product and Affiliate link identity, exported media review, scoped repairs and retries, separate live-publication authorization, and shot-level asset and approval traceability. Verified the documentation with `git diff --check`.

## Saved Flow presenter rule (2026-11-23)

- Recorded the project-wide requirement in AGENTS.md and linked it from CLAUDE.md and the Reel Master Prompt. Product videos and voiceovers use the saved พิธีกรคัดของเข้าบ้าน character and its Callirrhoe voice. Reuse matching references and recordings, synthesize only needed lines, and preserve approved footage for audio-only fixes.

## JUDYDOLL #01 WAVE presenter voice revision (2026-11-23)

- Verified that the saved Google Flow character [พิธีกรคัดของเข้าบ้าน](https://flow.google.com/project/81d65799-15e1-4834-b708-4e17857d09ff/character/0e74b82c-79cb-43da-badb-dc5e6d520d35) uses Callirrhoe. Generated and downloaded the four approved lines from Flow’s Callirrhoe preview with the character’s Thai delivery direction. Used Thai phonetic spellings for JUDYDOLL and Shopee. No new video was generated.
- Exported `JUDYDOLL-01-WAVE-review-callirrhoe.mp4` with the original video stream and new narration. Matching video stream SHA-256, a full decode, FFprobe (15.00 seconds, 720 × 1280, 9:16), and Thai ASR verified the export and all four lines. The review MP4 and source WAVs are under `backend/.local/judydoll-01-wave-video/`. No Reel was published.

## JUDYDOLL #01 WAVE approved video preview (2026-11-23)

- The user approved all four stills. Set Flow Agent to Veo 3.1 Lite, 9:16, and one output per shot. Sent a separate video command with the approved 01–04 start frames. Rechecked those settings for the silent 03 retry and the locked-framing retakes of 01, 02, and 04. Restored the original muted-video display setting after downloading.
- The first 03 failed at Flow audio synthesis. The silent retry recovered the approved macro; later frames introduced a finger. Selected clean source sections across all four shots and trimmed out hand, brush, or transition artifacts. Preserved the single product, four-pan layout, shot order, and upper space in the closer.
- Saved the four selected Flow clips and `JUDYDOLL-01-WAVE-review.mp4` under `backend/.local/judydoll-01-wave-video/`. Used the Mac's Thai voice with the approved four lines for consistent narration. FFprobe confirmed an exact 15.00-second H.264/AAC export at 720 × 1280, 30 fps, 9:16. Decoded the whole file and checked beginning, middle, and end frames per shot. The [Flow project](https://flow.google.com/project/c904478e-448d-478b-ac2a-da34f48cedaf) retains the source generations. No publication was requested.

## JUDYDOLL storyboard from approved references (2026-11-23)

- After the user approved R01–R03, attached those three stills and the original #01 WAVE Shopee photo to one separate storyboard command in [Flow](https://flow.google.com/project/c904478e-448d-478b-ac2a-da34f48cedaf). Verified Agent image defaults at 9:16 and one output per shot.
- Downloaded four independent photorealistic stills in shot order. Checked the single peach-pink compact, four-pan layout where fully shown, and two left highlight textures in the macro. The wordmark and matte pink look lighter in the angled frames. The Shopee image is the authority for color and markings.
- Kept the 768 × 1376 Flow originals, verified the 765 × 1360 review copies are exactly 9:16, and saved the timing, planned Thai narration, and Flow frame links under `backend/.local/judydoll-01-wave-storyboard-v2/`. Waiting for storyboard approval. No video or audio was generated.

## Two-step prompt and JUDYDOLL product refs (2026-11-23)

- Split the Master Prompt into product analysis and reference images first, then a separate still storyboard prompt that consumes the reviewed reference set. Updated the workflow guidance and Studio's storyboard prompt. The Next.js webpack build and `git diff --check` passed.
- Verified #01 WAVE against the original Shopee SKU photo. Flow Agent generated three 1024 × 1024 reference stills for overhead pan layout, the front three-quarter material view, and the two left highlight textures. The warm translucent case and four-pan layout match the source wherever fully visible. Use the original source for exact lettering and color comparison.
- Original, reviewed reference images, comparison sheet, and Thai product analysis are in `backend/.local/judydoll-01-wave-references/`. The [Flow reference project](https://flow.google.com/project/c904478e-448d-478b-ac2a-da34f48cedaf) is separate from the earlier storyboard. Stopped at reference review per request.

## JUDYDOLL #01 WAVE still storyboard (2026-11-23)

- Verified the single JUDYDOLL HIGHLIGHT & CONTOUR 9g #01 WAVE Upgraded Version in the Shopee variant picker. Downloaded the matching original from the Shopee image CDN. Used it as the only reference for a 15-second product-only storyboard with no presenter.
- In the [JUDYDOLL Flow project](https://flow.google.com/project/d1948698-0b1a-432c-a29c-daa5cc0e7a11), set Flow Agent image defaults to 9:16 with one output and requested shots 01–04 as separate still images. Reviewed all four for photorealism, one compact, the peach-pink lid, the correct four pans where fully framed, and both left highlights in the macro. Embossing and lettering vary slightly in the generated stills.
- Preserved the downloaded 768 × 1376 originals and checked the 765 × 1360 review copies for exact 9:16 and one frame each. The source, shot plan, individual stills, and review sheet are in `backend/.local/judydoll-01-wave-storyboard/`. The storyboard is saved in Flow. Studio's draft form requires a presenter image. Awaiting explicit approval of the presented stills. No video generation or publication was requested.

## Live Safari Affiliate handoff passed (2026-11-23)

- With explicit authorization, set Safari Capture 0.4.0 to Allow for `127.0.0.1` and `affiliate.shopee.co.th` only. Verified the other listed sites still showed Ask.
- Selected the real JUDYDOLL HIGHLIGHT & CONTOUR 9g offer without a saved link. Safari opened the official custom-link form and prefilled the exact listing `1225687272/25923634164` and Sub ID `facebook25923634164`. Clicked **เอา ลิงก์** once. Studio showed the same short URL as Shopee, and a read-only SQLite query confirmed it was persisted for the JUDYDOLL product and Facebook channel.
- Opened the existing Storyboard form for JUDYDOLL and verified its title. Left Safari there and the loopback Studio servers running. The proxied API health check returned OK.

## Live Safari Affiliate test setup (2026-11-23)

- Upgraded the empty default local SQLite database to `73328a4a6c1f`. Alembic reported no drift. Started the production frontend and local API on loopback ports 3014 and 8001. The proxied health endpoint reported OK. Left both running for the user.
- Opened Studio in Safari and created a local trial workspace. Imported the observed JUDYDOLL HIGHLIGHT & CONTOUR 9g Shopee offer (item `25923634164`) manually into the workspace. Verified the home card and its missing Facebook link. Zero channel links existed before the live test.
- Safari Capture 0.4.0 is enabled and Safari showed Ask for `127.0.0.1` and `affiliate.shopee.co.th`. Requested confirmation to grant those two website permissions. The live generated-link callback, save and same-product Storyboard remain pending. Studio is open at the product discovery page.

## Studio product discovery home (2026-11-23)

- Implemented option A as the signed-in Studio home, with the Thailand trend-matched shelf, saved Shopee commission shelf, estimated baht per order sorting and a mobile jump. Added optional offer thumbnails in migration `73328a4a6c1f`. Existing offer snapshots work without images.
- Selection looks up the product's saved Affiliate link in the active workspace, defaulting to Facebook. When the link is missing, Safari Capture 0.4.0 starts the official custom link form with the exact listing and Sub ID filled in. After the operator clicks **เอา ลิงก์**, the bridge captures the new short link and Studio saves it against the selected item and channel. The manual form remains available. Both paths hand off to the existing catalog Storyboard.
- Verified the real Shopee listing, Sub ID form and returned short link by hand in Safari. Safari 0.4.0 was loaded for testing, but the new copy requires website access to local Studio and Shopee Affiliate before live bridge verification. The browser QA with an isolated API and simulated Safari bridge verified automatic initiation, callback, save and the same-product Storyboard. Also verified the existing link, wrong-product rejection, manual creation, sorting and mobile jump at 390 px.
- Backend pytest passed 22 tests with 3 FFmpeg-dependent skips. SQLite Alembic upgrade and drift check, Next.js webpack production build, extension syntax and fixture checks, and `git diff --check` passed.

## Four product discovery UI concepts (2026-11-23)

- Researched Webby-winning work by lululemon, Pinterest Predicts, NBC Big Board, and DVF Shopping Journey. Gemini Canvas returned errors. Google AI Studio Build confirmed Gemini 4 Neon and generated the [interactive comparison](https://aistudio.google.com/apps/1b395640-8fae-4271-bb9a-7d2e878c8e45?showPreview=true&showAssistant=true&fullscreenApplet=true) with four Thai layouts on a shared mock catalog.
- Verified desktop switching across A–D, inspected the mobile view of A, and tested both the existing link and simulated link creation through the corresponding Storyboard summary. The prototype uses fictional data and performs no real Shopee or Flow operation. Studio application code is unchanged.

## Start-of-day status (2026-11-23)

- Phase 7 remains active. The latest verified live trend trial reached the saved GAMBOL LM11005 Facebook Affiliate link. The GAMBOL voice revision is ready for preview review, with shot 01 still silent. SMEG ASMR awaits storyboard approval.
- No Studio listeners were present at the time of this check. Local health requests with proxy bypass could not connect on ports 3000, 3014, 8001 or 8014.
- Backend pytest in the existing virtual environment with `PYTHAINLP_OFFLINE=1` passed 22 tests and skipped 3 real-media tests because FFmpeg and ffprobe were unavailable on PATH. `npm run typecheck --prefix apps/web` and `git diff --check` passed. The branch has uncommitted work from previous sessions.

## Local server check (2026-11-23)

- On request, sent SIGTERM to all 18 identified project listeners, including the Studio web, API, Meta OAuth spike, and QA instances. A follow-up `lsof` showed only macOS and Logitech listeners.
- `curl` returned HTTP 200 for the Studio home page on ports 3000 and 3014. `/api/v1/health` returned `{"status":"ok"}` through both web ports and directly on API ports 8001 and 8014.

## GAMBOL LM11005 voice revision preview (2026-11-23)

- Used the approved start frames and Veo 3.1 Lite at 9:16 to try spoken retakes of shots 01 and 02. Flow audio synthesis failed for both the existing shot 01 line and the separately approved alternative. Shot 02 rendered speech and mouth motion in the same take, and local Thai transcription recovered the letters LM and all five digits in order.
- Exported `GAMBOL-LM11005-review-scene-02-voice.mp4` in the product's `video-preview` folder. It runs 18.50 seconds to retain the full model-number reading. Keeps the existing silent opening and the silent shots 03–04. Frame checksums for shots 03–04 match the previous preview. No Reel was posted.

## GAMBOL LM11005 approved storyboard video preview (2026-11-23)

- Generated and downloaded scenes 01–04 in the [existing Flow project](https://flow.google.com/project/49dc28b5-7a32-4143-a11f-0747280bf37d) using Veo 3.1 Lite and vertical 9:16 start frames from the approved black BK-LV05 storyboard. Flow Agent could not synthesize scene 01 audio. Recovered the clip through Flow Frames with the user-approved muted output setting, then verified that the setting was restored to off.
- Stitched the four shots in storyboard order and verified a 15.00-second H.264 preview at 720 × 1280. The red LFC patch is legible in the sampled scene 03 frame. The preview is silent because scene 01 has no speech and scene 02 mispronounces LM11005. The preview and source clips are in the product's `video-preview` asset folder. No Reel was posted.

## SMEG ASMR unboxing storyboard (2026-11-23)

- Regenerated stills 04 and 06 using the catalog photo. In 04 the left hand steadies the base from the left and the right hand reaches the cap from the right. Reviewed both stills for the spaced silver SMEG lettering. These are generated approximations of the reference. Awaiting approval of the two revised stills before any video generation.
- Used the existing SMEG Flow Agent project and catalog image to create six portrait stills for a 25-second hands-only Shopee storyboard. Revised panels 02, 03 and 05 for numbering and continuity. Checked the final contact sheet against the catalog for the bottle profile, pastel-blue color and silver cap. Some fine lettering still varies, and the generic kraft carton is a staging prop because retail packaging was unavailable. Awaiting user approval of the displayed stills. No video or audio was generated.

## GAMBOL storyboard scene 03 revision

- Cropped the black BK-LV05 strap and red LFC patch directly from the saved Shopee listing photo. Replaced only scene 03 and preserved its number and the gutters in a lossless PNG. Pixel comparison against the original verified that scenes 01, 02 and 04 are unchanged.
- Uploaded and verified the [revised still](https://flow.google.com/project/49dc28b5-7a32-4143-a11f-0747280bf37d/edit/23a89ae8-e23a-4101-9b3e-329a5c75ef00) in the original GAMBOL project. Awaiting review of the revised image. No video generation or posting was requested.

## GAMBOL Liverpool FC storyboard

- Selected the black BK-LV05 variant for the linked LM11005 offer. Used the actual Shopee Affiliate product photo and the existing presenter reference to generate one photorealistic [four-scene still in Flow](https://flow.google.com/project/49dc28b5-7a32-4143-a11f-0747280bf37d/edit/fd801d79-af65-4f0e-80f4-07cecbe93165). The close-up shows the correct black shape, red tag and white sole edge, with small lettering on the tag differing from the product photo.
- Saved the 768 × 1376 original to the product assets and verified a byte-identical readback from the linked Studio storyboard. The still is awaiting review. No video or publication was requested.

## Gadget unboxing references (2026-11-23)

- Searched for ASMR gadget unboxing channels and checked indexed YouTube channel and video descriptions. References include [The Unboxing ASMR](https://www.youtube.com/@TheUnboxingAsmr), [Unbox Lab](https://www.youtube.com/@asmrunboxingtechlab), and [ASMR Unboxing](https://www.youtube.com/@ASMRUnboxingOfficial). Direct video playback was unavailable during the search. No code changes.
- Applied the international channel filter of more than 100,000 subscribers. Verified public counts for TheRelaxingEnd (9.67M), Dr Debox (1.24M), Tech Unboxing (1.08M), and ASMR Unboxing (103K) and located examples of gadget unboxing for each.
- Shortlisted five YouTube Shorts with roughly 1.4M–23.8M cumulative views from international channels over 100K subscribers. The [DJI Osmo Pocket 4 Short](https://www.youtube.com/shorts/kEbC55D2NPY) is the closest reference for a small Shopee gadget, and the [ASUS ROG Phone 5 Short](https://www.youtube.com/shorts/CjHe8gN-hAU) covers premium packaging. Counts and formats were sourced from indexed YouTube metadata and public trackers.
- Reviewed frames across the 34.24-second DJI Short and drafted a 25-second Shopee shot list. The source uses an overhead unboxing, brief accessory inserts and a held product shot from roughly 27 seconds. Audio cues for the Shopee shot list are recording suggestions based on visible actions. The original audio track was unavailable for direct review.

## Live trend-to-Affiliate trial (2026-11-23)

- Connected the isolated Studio to the official Thai Google Trends RSS using the macOS CA bundle with TLS verification enabled. Selected the live Florian Wirtz trend (2,000+ searches), searched Liverpool in Shopee Affiliate, and imported three observed offers. The Studio filter used at least 1,000 sales and 7% commission and returned the GAMBOL Liverpool FC LM11005 offer, which showed 2,000+ sold at THB 165 and 7% commission.
- Followed the selected offer from Studio, generated a tagged short link in Shopee's advanced link form, and saved it back to the same Studio product for Facebook with Sub ID `fblfcgambol01`. Verified readback in Safari and through the Studio API. This run used the existing isolated Studio workspace with real provider data. No video generation or posting was requested.

## Studio trend-to-Affiliate workflow

- Connected the Trends, Shopee offer filters and Affiliate setup pages. The selected trend pre-populates the offer query, and the selected offer carries through to the Shopee detail link and Studio form. The selection is scoped to the workspace and survives reload in the same browser tab. Studio reuses the catalog record for the same Shopee listing and saves each channel link through the existing API.
- Verified both a controlled Trends feed and the manual keyword route in Chromium. Filters reduced three QA offers to one, the selected offer persisted across reload and sign-in, a plain product URL was rejected in the Affiliate field, and Facebook and TikTok example links saved under distinct Sub IDs. Google Trends live RSS was unavailable from the QA backend during this run. The production build passed. The Shopee portal remains the step for generating the actual Affiliate URL.

## SMEG storyboard trial (2026-11-23)

- Ran a four-shot storyboard for the catalog pastel-blue SMEG × 24Bottles WBF01PB 500 ml in the isolated Studio workspace. Safari opened the existing SMEG Flow project and uploaded the product reference, but stopped while confirming the attachment. Finished adding the original presenter reference in Flow, verified Image 9:16 with one output, and created one [new still](https://flow.google.com/project/834ad336-5de3-4e7f-8f43-57cdfdf2627e/edit/433153b3-280d-422e-9010-e643ccfb1538).
- Imported the original 768 × 1376 JPEG through the Studio endpoint, verified byte-identical readback, and reopened it in Safari. The four panels are numbered 01–04. The presenter and bottle are visually consistent, with the grip partly obscuring the front lettering in panel 02. No video or publication request was submitted. UX changes were paused.

## Automation and agent inventory (2026-11-23)

- Reviewed the Studio backend, Safari extension, Flow operating instructions, and verification records. The Safari storyboard handoff explicitly disables Flow Agent and selects still-image mode. Agent-led Flow video generation remains an operator-approved workflow outside the Studio worker. No runtime checks or external operations were performed for this inventory.

## Safari storyboard handoff and live Flow readback

- Added Safari extension 0.3.0 and a Studio button that transfers the saved still-image prompt and two references to a new Flow tab, verifies Image mode, 9:16 and one output, and returns the matching image to the private Studio review screen. For live QA a temporary extension pointed to an isolated Studio instance on port 3020. The standard extension targets port 3014.
- In real Safari, the extension attached the GHAOHES product and presenter images through Flow's Upload media control and entered the 12-shot prompt. Flow did not start from the extension's simulated click. A direct click on the verified Image Generate button started the job, and Safari automatically imported the [new Flow image](https://flow.google.com/project/81d65799-15e1-4834-b708-4e17857d09ff/edit/c4ab6795-8e57-4eb9-a513-1858f39db3ee) into Studio. The saved 768 × 1376 JPEG differs from the earlier direct Flow sample. No video or publication was requested.
- Review flagged missing panel numbers, uneven panel boundaries and label text that differs from the source. Tightened the grid and numbering instructions after the live test. Next.js build, backend tests (22 passed, 3 skipped) and the Flow adapter simulation (3 passed) verified the code paths.

## Google Flow MCP feasibility (2026-11-23)

- Public documentation review found community wrappers for the Flow browser UI and no published Google MCP for Flow projects or Flow Agent. Google's Genmedia MCP uses Google Cloud media APIs. See [Flow Help](https://support.google.com/flow/), [community wrapper](https://github.com/ParkSangGwon/google-flow-mcp), and [Google Cloud Genmedia MCP](https://github.com/GoogleCloudPlatform/genmedia-creative-studio/blob/main/experiments/mcp-genmedia/README.md). No installation or live generation was performed.

## Studio storyboard handoff to Google Flow

- Added **เตรียม Storyboard** to ranked Shopee offers and Google Trends product opportunities. Studio saves the exact variant, verified details, up to 12 shots, and two private reference images in the workspace. It copies a still-only photorealistic prompt and opens Flow. The operator attaches references in Flow and imports the downloaded still for review in Studio.
- In an isolated browser run, selected the saved floor-wipes offer, saved a 12-shot plan with the original product and presenter reference files, opened the actual Flow page via the clipboard action, and imported the existing 768 × 1376 still. Verified the review image persisted through reload and sign-in. No new Flow generation or publishing request was submitted.
- The Next.js production build passed. The backend suite passed with 22 tests and 3 skips, including storyboard upload, readback, invalid image rejection and workspace isolation. Ran with a writable `PYTHAINLP_DATA` directory and `PYTHAINLP_OFFLINE=1`.

## Photorealistic storyboard panels

- Updated `AGENTS.md` and `CLAUDE.md` to require and review photorealistic stills in every Flow storyboard panel, including inserts and revisions, before user approval. This change updates workflow instructions.

## Revised 12-panel floor-wipes storyboard

- Uploaded the [revised still](https://flow.google.com/project/81d65799-15e1-4834-b708-4e17857d09ff/edit/8dc03b8d-d5f5-4f0d-b20d-9d415e34d7a6) to the existing floor-wipes collection and verified it in Flow.
- Panels 04, 05 and 12 use crops from the actual listing photo. Panel 06 arranges five copies of the photographed pack. A pixel comparison confirmed that the other eight panels, including the presenter frames, match the original.
- The revised still is awaiting user review. No video or audio generation was submitted.

## Google Flow storyboard approval

- Added a project-wide agent rule to create and review a still storyboard before submitting any Flow video-generation request. The rule covers single shots, batches, revisions, and added shots. See [AGENTS.md](../../AGENTS.md#google-flow-workflow).
- Set vertical 9:16 framing for every storyboard panel and require verified 9:16 and Veo 3.1 Lite settings before every video-generation request, including retries.
- The floor-wipes test produced a 12-panel storyboard with the existing presenter and package references in Flow. The label and five-pack shots need review before any video generation. This task updates operating instructions only.

## SMEG Reel with a product photo in the first frame

- Planned the Reel in the Gemini web app, then used one Veo 3.1 Lite generation in Flow for the notebook-and-pen insert. Replaced unsupported product benefit wording with the visible item details. No API billing was enabled.
- Added a product-photo-first mode to the Flow MP4 import. Chromium imported the actual Flow clip, selected the new mode and played render `5e12819c-46ee-49df-9261-b67189d8d529`. Frame inspection confirmed the real bottle at 0 seconds, the Veo insert from 4–7 seconds, and real product photos for the remaining two shots. FFprobe confirmed 15 seconds at 1080 × 1920, H.264 at 30 fps. The preview has no publication record. The web build and 37 tests passed.

## Google Flow opening shot and SMEG Reel

- Generated one vertical 720p desk shot in Google Flow with Veo 3.1 Lite using the signed-in account. Flow's settings showed 10 credits for one output. Downloaded the 7.93-second original and imported it in Studio. No API billing was enabled.
- Chrome verified the local Studio upload, optional Thai opening caption, and playback of the actual FFmpeg result. Render `3f075866-94d2-471a-b454-a8a9d61529e9` combines four seconds of Flow footage and two real product photos. FFprobe confirmed 15 seconds at 1080 × 1920. The preview is muted and has no Meta publication record. The web build and 37 tests passed.

## Purchased-product asset collection and Reel preview

- Added a workspace-scoped screen for verified purchases. Once direct image URLs are registered, one action downloads the originals into source folders and renders a private FFmpeg Reel. Purchase verification and search-result selection currently happen before registering the item.
- Registered the SMEG × 24Bottles WBF01 from the completed Shopee purchase already verified in Safari. In Chromium, selecting it and clicking the render button downloaded one Shopee gallery image and two images found through search, and played preview `28e84246-f334-42e3-813a-eb622b85fc5d` at 1080 × 1920 for 15 seconds. The catalog photos show the pastel-blue variant. The original purchase color and publication rights are unverified.
- The production web build and 37 backend/publish-spike tests passed. The preview requires workspace access and does not enter the publishing render library.
- Added a single authenticated collection endpoint and per-render source manifests. Verified a second completed purchase in the existing Shopee session, COTTO CT9901#SA(HM), and selected two exact-model references through image search. The endpoint downloaded three originals and generated a 1080 × 1920, 15-second preview. Chromium verified the COTTO purchase source, asset list and playback in Studio. Continuous buyer-history and Google image discovery still need supported connectors. No publication was created.

## Phase 7 opportunity-to-Reel preview (2026-11-22)

- In Studio, **เตรียม Reel** passes the selected product and trend or manual query into an editable three-scene script. FFmpeg burns each caption into the preview at 0–5, 5–10 and 10–15 seconds. The saved preview remains available when the editing session ends.
- Chromium selected the existing Scotch-Brite microfiber kitchen cloth from a controlled ranked result because the live workspace had no matching trend. It opened the video form, edited the script, uploaded three original graphics already used for this product and submitted one real FFmpeg render. Render `d593d7e9-9682-46b7-b2a6-975f01fedec5` completed and loaded in Studio.
- FFprobe confirmed H.264/AAC, 1080 × 1920, 30 fps and 15.00 seconds. Inspected frames at 2, 7 and 12 seconds for legible Thai text. The authenticated download matched the saved file byte-for-byte. The preview has no Meta publication or simulation record.
- The web production build and 36 backend/publish-spike tests passed. Gemini, Veo and Shopee Open API remain deferred.

## Phase 7 product opportunity ranking (2026-11-22)

- The Google Trends page ranks up to five distinct products using estimated search volume (25 points), keyword relevance (35), attributed clicks (15) and eligible unique orders (25). CSV history covers 30 Bangkok calendar days. The page shows each component and distinguishes missing data from an observed zero.
- An isolated integration test imported click and order CSVs through the normal upload API. The first-ranked product received 62/100 from 2 attributable clicks, 1 eligible unique order and a trend showing 2,000+ searches. The test covered duplicate clicks, multiline orders, cancelled and unpaid orders, ambiguous Sub IDs, workspace isolation and the date boundary.
- Chromium verified the real Thailand feed in the existing Studio. It showed 10 trends, no matches and no imported Affiliate report rows in the checked workspace. A controlled response verified score breakdown, missing-data labels, filters, deduplication across trends and navigation to inventory. The production build and 35 backend/publish-spike tests passed.
- Before committing, the Studio API returned a current Thailand RSS snapshot fetched at 17:40 Bangkok time. The 24-hour view had 10 trends, 0 matched trends and 0 Affiliate CSV report groups. All 35 tests passed again.
- Gemini, Veo and Shopee Open API remain deferred.

## Phase 7 Google Trends (2026-11-22)

- Studio reads Thailand's official Google Trending Now RSS and shows 4- and 24-hour windows, freshness, approximate searches and Google Explore links. It matches Thai and Latin tokens against saved Shopee product names within the selected workspace. Manual keyword matching works independently of the feed.
- At 17:28 Bangkok time the live Studio API returned 10 Thai trends for 24 hours and 3 for 4 hours. The workspace had one Shopee product and no automatic match to that live snapshot. Searching `ผ้าไมโครไฟเบอร์` returned the saved Scotch-Brite cloth with the terms `ผ้า`, `ไมโคร` and `ไฟเบอร์`. An unrelated football query returned no matches.
- Chromium verified the live feed, time and keyword filters, the matching-only filter, and opening a saved product from manual search. `PYTHAINLP_READ_ONLY=1 PYTHAINLP_OFFLINE=1 backend/.venv/bin/python -m pytest backend/tests spikes/phase0_publish/tests -q` passed 34 tests with FFmpeg on PATH. The production web build and Alembic schema check passed.
- A controlled RSS fixture verified automatic matching to a relevant product, workspace isolation, and exclusion of products from other domains. A cache test verified the fallback during a feed outage.
- The feed has no category field. The opportunity score was added in the follow-up above. Gemini, Veo and Shopee Open API remain deferred.

## Phase 6 staging operations (2026-11-22)

- Started the isolated Compose stack on Docker Desktop. PostgreSQL 17, the API, the web proxy, the campaign worker, and Prometheus were reachable. Existing Studio data and the staging secret were kept separate.
- The staging smoke test rendered an MP4, completed one simulated campaign, verified its simulated Affiliate comment, and received HTTP 403 for both live publish and live campaign creation. Prometheus reported a fresh worker heartbeat.
- Backup `20261122T101418201265971Z` passed the SHA-256 and isolated restore checks. The restored PostgreSQL database held one workspace, one render, and one campaign item. The completed MP4 was present. A restricted copy of the backup was exported under `backend/.local/staging-backups/`.
- Prometheus validated six rules and passed the stale-heartbeat test. It reported the backup timestamp after the API and worker restarted. The backend and publish-spike test suite passed 32 tests. The GitHub staging job was added and its checks were exercised locally.
- Billing and live staging writes remain off. Hosted deployment, automatic off-host backups, and external alert routing remain pending. See `docs/ops/STAGING.md`.

## Local campaign queue (2026-11-22)

- Phase 5 added campaign drafts, Bangkok scheduling, approval, pause, resume, cancellation, and job status in Studio. The separate worker persists jobs and its lease in the database. It reuses the existing Meta publication ledger when reading a requested post or comment.
- An isolated SQLite load test reopened a database session for each worker tick. The persisted results were 500 completed jobs, 500 verified simulated comments, and 0 live publications. The next tick found no due work. Browser verification created a draft, activated it, paused it, resumed it, and showed one completed simulation after a separate worker process ran.
- Backend and publish-spike tests passed (32). The web production build and the SQLite migration and Alembic schema check passed.
- Live campaigns are off by default. No live post or comment was made in this phase. The single-Page connection, production Celery deployment, and multi-Page scheduling have separate acceptance work.

## Shopee Affiliate CSV reporting (2026-11-22)

- Studio imports Click Report and Order Report CSVs into the selected workspace. The report groups clicks, unique orders, and commission by channel and Sub ID. Imported Sub IDs can match saved Studio links.
- Browser verification uploaded both fixtures into an isolated SQLite database. Import accepted 3 unique clicks from 4 rows and 5 order lines across 3 unique orders. The report showed ฿16.13 estimated and ฿6.00 confirmed. Filtering to Facebook and `fbcloth01-sale` showed ฿10.13 estimated and hid the TikTok row.
- The backend regression test covered repeat imports, an order status update, an older export, repeated order-level commission, invalid CSV rows, and workspace isolation. The production build, SQLite migration, and Alembic schema check passed.
- The connected Shopee account showed no rows for the checked periods and did not offer CSV downloads. The Studio workspace has no report rows. Shopee Open API remains paused.

## First live publication from Studio

- Enabled live posting in the local Studio for the configured workspace owner and the Page คัดของเข้าบ้าน.
- Created a Shopee Affiliate link for Scotch-Brite kitchen microfiber cloths (pack of two) with Facebook Sub ID `fbcloth01`. Studio rendered one 15-second Reel from three original graphics.
- The Studio interface submitted one public Reel and one Affiliate comment, then showed `published` and verified the Page-authored comment and Affiliate URL from Meta Graph API. The backend retained the publication and comment IDs. [Reel](https://www.facebook.com/reel/1974853066822019/) · [Verified comment](https://www.facebook.com/reel/1974853066822019/?comment_id=1793026762213749)
- Meta Graph API v27.0 returned Reel ID `1974853066822019` with `publish_status=published`. The comment creation response returned `1974853066822019_1793026762213749`; listing Reel comments returned `122097553173560732_1793026762213749` with the expected Page author, Affiliate URL and disclosure. Studio recorded `comment_verified=true`.

## Studio Meta connection

- Added workspace-owner access for one configured Facebook Page, publication state per render, and Reel and comment read-back. The Studio can post a Facebook-channel Affiliate comment once Meta confirms publication. The existing simulation remains usable.
- Verified the existing Magiclean Reel and its Affiliate comment from the Studio interface using Meta Graph API v27.0 with writes disabled. The Studio displayed the published status, Page author, Affiliate link and comment permalink.

## Earlier Affiliate results preview (2026-11-22)

- The original **ผลลัพธ์ Affiliate** view used 60 days of fixed demo data for clicks, orders and commissions. It supported date and channel filters, period comparisons, and performance by Sub ID. The two trends views used a fixed seven-day window with a Shopee ranking example and Studio order growth by product and channel.
- Adding a product from a card pre-fills its name in the existing product form. The user supplies the source URL. The browser keeps the sample-to-product association per workspace and uses it to reopen the saved product. Shopee reports and live rankings are pending the provider integration.
- Safari verification on an isolated SQLite database covered opening the report, switching to 30 days, switching to Studio order growth, and saving and reopening a product through a trend card.
- Browser verification on an isolated SQLite database also covered the Facebook channel filter, comparison toggle, valid and reversed custom date ranges, and reopening the saved trend product after reload. A second workspace showed its own product associations.
- ImageGen produced the three sample product photos in `apps/web/public/affiliate-demo/` using the built-in tool with this prompt.

  > Product mockup for a Thai affiliate dashboard. A single wide horizontal catalog contact sheet with exactly three equally sized side-by-side scenes, no gutters, each object centered in its own third with ample margin. Left: ivory compact portable handheld fan upright on light mint sage backdrop. Middle: dusty blue 750ml stainless steel insulated tumbler with handle and lid on soft powder blue backdrop. Right: cream modular drawer organizer tray containing two small neatly folded cloths on warm pale peach backdrop. Refined photographic ecommerce thumbnails with soft daylight, subtle shadows and believable materials, three isolated products, shot from eye-level slight three-quarter angle. No text, logos, hands, or watermark.

## First live Reel test (2026-11-22)

- Published one 15-second Magiclean test Reel using the Meta Graph API on คัดของเข้าบ้าน. The API reported `publish_status=published` and the user confirmed the Reel was visible. [Published Reel](https://www.facebook.com/reel/1474154981527533/)
- The original Magiclean publication and comment tests ran through direct Graph API calls before the Studio connection was implemented.
- The test caption and channel link are recorded in `drafts/fbkitchen01/`. The rendered previews and source photos are kept locally.
- Posted one Affiliate comment via Graph API v27.0 at `POST /1474154981527533/comments`. A direct GET by the returned comment ID and `GET /1474154981527533/comments` both confirmed the same author, message, and permalink. Meta returned `1474154981527533_1139470178465538` on creation and `122097541725560732_1139470178465538` when listing the Reel comments. The IDs share a comment suffix, while the prefixes are the video ID and post ID respectively. [Verified comment](https://www.facebook.com/reel/1474154981527533/?comment_id=1139470178465538)

## Phase verification follow-up

- Recorded Thai Shopee operations in `docs/api/SHOPEE_AFFILIATE_ENDPOINTS.md`. Account scope and authenticated calls remain unverified.
- Added GitHub Actions configuration for migrations, backend tests and web build. The hosted job has not run.
- Backend tests passed (13), including the 100-row CSV replay and workspace isolation check. Publish spike passed (15), including 500 simulated jobs with a finish timeout on every job and no duplicate Reels. Frontend type checking passed.


## Shopee Affiliate access (2026-11-22)

- The user decided to defer the Open API application because the account does not currently meet Shopee's criteria. No application was submitted.
- Shopee's Affiliate account is accessible and shows the Facebook Page คัดของเข้าบ้าน as verified. The Open API screen says the account does not have access. Shopee's application states more than 1,000 orders per month, a valid payout account, evidence of audience performance, and an operating plan among its criteria.
- Shopee's custom-link tool is available at https://affiliate.shopee.co.th/offer/custom_link. Use its generated link with manual product entry or CSV import. The dashboard requests payment and tax details.
- The local studio was started against a persistent SQLite database with FFmpeg on PATH. A real product and image-use permission are still needed.

## Local MVP slice (2026-11-22)

- The user chose to defer public publishing and build the single-product path across Phases 1–4 first. Three Luna medium agents implemented foundation, products and rendering. The main agent integrated migrations, a Next.js UI and the existing Meta test double, then reviewed and verified the system.
- The registered API covers authentication and workspaces, manual product entry/edit, CSV ingest, image-rights gating, three-image rendering and protected preview. Simulations record separate publish and comment states, reconcile a timeout without issuing a second finish request, and return the same result for an identical replay.
- The browser test used synthetic images and reached `published`, `posted`, and verified comment read-back in the local simulator. Local API verification also covered malformed CSV rows, duplicate source URLs and cross-workspace access. Alembic reached head and reported no schema drift on SQLite and PostgreSQL 17. PostgreSQL also rejected a cross-workspace foreign key, and the same product-to-simulation flow passed against PostgreSQL.
- The separate Meta OAuth spike confirmed via read-only Graph API that the existing token still identifies the renamed Page คัดของเข้าบ้าน. The studio has no live Meta publishing route. No Reel or comment was sent to Facebook.
- Verification: `uv run --project backend --extra test pytest backend/tests -q` with FFmpeg on PATH → 12 passed, including mixed JPEG/PNG/WebP input. Existing publish and OAuth spikes → 14 and 15 passed. `npm run build --prefix apps/web` and `npm run typecheck --prefix apps/web` passed.
- Run instructions are in `README.md`. Production workers, managed media storage, staged deployment, and a real Shopee product/affiliate link are still pending.

## Earlier feasibility work

## Current state
- Phase: 0 (in progress)
- Live Meta OAuth succeeded in Development Mode with Facebook Login for Business. The callback returned exactly one sandbox Page with `CREATE_CONTENT` and `MODERATE`, all five configured Page permissions, and no declined permissions.
- OAuth tokens are encrypted in the ignored `spikes/phase0_meta/.secrets/` directory. The sanitized callback receipt is in the ignored `spikes/phase0_meta/evidence/` directory.
- FFmpeg 9.0.2 rendered a synthetic 1080×1920, 30 fps, 15.000-second H.264/AAC video. Both Meta test suites passed locally (15 OAuth tests and 14 mock publishing tests).
- The live Reel publish, comment read-back, and Reel listing during processing remain pending. Shopee Affiliate TH Open API access and image/data reuse terms remain unverified.

## Live verification (2026-11-22)
- Meta permitted the loopback redirect automatically in Development Mode. The Business Login configuration uses a User access token and matches the five scopes in `.env.example`.
- The initial OAuth callback reached localhost but Python reported a TLS verification error. Starting the spike with `SSL_CERT_FILE=/etc/ssl/cert.pem` fixed certificate validation, and a fresh OAuth attempt succeeded.
- The Page token resolved to the sandbox Page via a read-only Graph API call. External publishing remains on hold until the single-product workflow has been reviewed and approved for a public test.

## Initial Phase 0 work (2026-11-22)
- Goal: Phase 0 documentation + local feasibility planning.
- Files changed: `docs/product/PRD.md`, `docs/api/API_FEASIBILITY.md`, `docs/architecture/SYSTEM.md`, `docs/architecture/ERD.md`, `docs/decisions/ADR-0001..0005`, `docs/backlog/PHASE_00_BACKLOG.md`, `docs/phases/PHASE_00.md`, `docs/agent/*`, `spikes/`, `.gitignore`.
- Commands/tests run and actual results: pytest as above → 14 passed; `bash -n spikes/phase0_video/render_sample.sh` → OK; render not executed (no ffmpeg).
- Decisions made: modular monolith + Celery; org_id + composite FKs, 404 on cross-tenant, RLS to evaluate in Phase 1; reconcile-before-retry with `unknown` / `failed_safe_to_retry` + settle window; ingest = manual + CSV; video = H.264/AAC 1080×1920 30 fps 15/20/30 s.
- Blockers / permissions needed: B1 Meta App + test Page + test user role; B2 Shopee Affiliate TH Open API access; B3 Shopee image/data reuse terms; B4 ffmpeg on dev machine; B5 Reel `video_id` as comment target unverified; B6 Meta doc inconsistencies (`finish` vs `complete`, `publish_video`).
- Open product assumptions to confirm with user: A1 Thailand market, A2 English UI first (Thai later), role matrix.

## Next action
Live Studio publication and comment read-back passed in the configured local workspace.
