"""Compose a local Google Flow clip with saved product photos."""

import json
import math
import subprocess
from pathlib import Path

from .renders import _run_render, _write_scene_captions

MAX_FLOW_BYTES = 48 * 1024 * 1024
FPS = 30
MAX_OPENING_SECONDS = 4


def opening_frames(path: Path, cap: int = MAX_OPENING_SECONDS) -> int:
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-protocol_whitelist", "file", "-f", "mov",
            "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,duration",
            "-of", "json", str(path),
        ], capture_output=True, text=True, timeout=15, check=True)
        data = json.loads(result.stdout)
        video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
        duration = float(video.get("duration") or data["format"]["duration"])
        width, height = int(video["width"]), int(video["height"])
        if (not math.isfinite(duration) or not 2 <= duration <= 45 or
                not 144 <= min(width, height) or max(width, height) > 4096):
            raise ValueError("Invalid dimensions or duration")
        return math.floor(min(duration, cap) * FPS)
    except (subprocess.SubprocessError, KeyError, TypeError, ValueError, StopIteration) as exc:
        raise ValueError("เลือกไฟล์ MP4 ที่เล่นได้ ความยาว 2–45 วินาที") from exc


def render_flow_preview(
    opener: Path, photos: list[Path], output: Path, product_name: str, opening_text: str,
    *, product_first: bool = False,
) -> float:
    flow_frames = opening_frames(opener, 3 if product_first else MAX_OPENING_SECONDS)
    caption_end = "ดูรายละเอียดที่หน้าสินค้า"
    if product_first:
        first_photo = 4 * FPS
        remainder = 15 * FPS - first_photo - flow_frames
        if len(photos) == 3:
            middle = remainder // 2
            photo_frames = [first_photo, middle, remainder - middle]
            order = [1, 0, 2, 3]
            captions = [opening_text, "", product_name, caption_end]
        else:
            photo_frames = [first_photo, remainder]
            order = [1, 0, 2]
            captions = [opening_text, "", f"{product_name}\n{caption_end}"]
    else:
        remainder = 15 * FPS - flow_frames
        photo_frames = [remainder // 2, remainder - remainder // 2]
        order = [0, 1, 2]
        captions = [opening_text, product_name, caption_end]
    frame_counts = [flow_frames, *photo_frames]
    boundaries = [0.0]
    total = 0
    for index in order:
        total += frame_counts[index]
        boundaries.append(total / FPS)
    _write_scene_captions(
        captions, output.parent / "captions.ass", boundaries,
    )
    filters = [
        "[0:v:0]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1,fps=30,format=yuv420p,"
        f"tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame={flow_frames},setpts=PTS-STARTPTS[v0]",
    ]
    for index, frames in enumerate(photo_frames, 1):
        filters.append(
            f"[{index}:v]zoompan=z='1.005+0.00025*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':"
            f"d={frames}:s=1080x1920:fps=30,setsar=1,format=yuv420p[v{index}]"
        )
    sequence = "".join(f"[v{index}]" for index in order)
    filters.append(f"{sequence}concat=n={len(order)}:v=1:a=0,ass=filename=captions.ass[v]")
    inputs = [arg for photo in photos for arg in ("-i", str(photo))]
    _run_render([
        "ffmpeg", "-v", "error", "-y", "-protocol_whitelist", "file", "-f", "mov", "-i", str(opener),
        *inputs,
        "-f", "lavfi", "-t", "15", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-filter_complex", ";".join(filters), "-map", "[v]", "-map", f"{len(photos) + 1}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-t", "15", "-movflags", "+faststart", str(output),
    ], output)
    return flow_frames / FPS
