# ADR-0005 — Video spec: FFmpeg MP4 H.264/AAC 1080×1920, 30 fps, 15/20/30 s

- Date: 2026-11-22
- Status: Accepted (spec checked against documentation; render NOT RUN, ffmpeg not installed)
- Context: Meta documents for Reels (Reels publishing guide, v27.0): 9:16, 1080×1920 recommended (min 540×960), 24–60 fps fixed, 3–90 s, H.264/H.265, 4:2:0, closed GOP 2–5 s, progressive; audio AAC-LC stereo 48 kHz ≥128 kbps.
- Decision: Output MP4 (`+faststart`), H.264 High, yuv420p, 1080×1920, 30 fps CFR, closed GOP 2 s (`-g 60 -sc_threshold 0`), AAC-LC stereo 48 kHz 128 kbps (silent track when no music), durations 15 / 20 / 30 s. All within documented limits. Max file size is not stated in the guide (UNVERIFIED); enforce a conservative internal cap and measure.
- Alternatives considered: H.265 (smaller, weaker compatibility); 720×1280 (above minimum but not recommended); no audio track (spec lists audio settings; silent AAC avoids ambiguity — UNVERIFIED if audio is mandatory).
- Consequences: Templates are defined by duration and scene timing; ffprobe validation gate before publish; music requires licensing.
- Verification / revisit trigger: Run `spikes/phase0_video/render_sample.sh` where ffmpeg exists; then upload one sample to a test Page.
