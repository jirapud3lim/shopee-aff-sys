# Phase 0 spike — FFmpeg sample render

**Verified on 2026-11-22 with FFmpeg 9.0.2.** The script rendered three original synthetic images. ffprobe reported 1080×1920, 30 fps, H.264 yuv420p, stereo AAC at 48 kHz, and a 15.000-second duration.

`render_sample.sh img1 img2 img3 [out.mp4]` builds a 15 s, 1080×1920, 30 fps, H.264 (High, yuv420p, closed 2 s GOP) + silent stereo AAC 48 kHz/128k MP4 with ken-burns zoom and 1 s crossfades, then checks it with `ffprobe` (size, duration). Settings follow the Meta Reels spec in `docs/api/API_FEASIBILITY.md`.

To render a sample: `./render_sample.sh a.jpg b.jpg c.jpg out.mp4`. Use only images you have rights to.
