"""Bounded, local-only product video rendering for the Phase 3 vertical slice."""

from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from itertools import accumulate
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import DateTime, ForeignKeyConstraint, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .auth import require_workspace
from .db import Base, get_db
from .products import Product
from .reel_timeline import FPS, REEL_FRAMES, SCENE_TEXT_LIMIT, ReelPlan, TimelineShot, compile_timeline

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/renders", tags=["renders"])
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = 30 * 1024 * 1024
MAX_MEDIA_BYTES = 64 * 1024 * 1024
MAX_CLIP_BYTES = 48 * 1024 * 1024
MAX_MEDIA_FILES = 12
MIN_PHOTOS = 4
CLIP_TYPES = {"video/mp4", "video/quicktime", "video/x-quicktime"}
MAX_IMAGE_PIXELS = 40_000_000
RENDER_TIMEOUT_SECONDS = 180
IMAGE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / ".local"


def data_dir() -> Path:
    """Runtime data root. Override with STUDIO_DATA_DIR; RENDER_ROOT still wins for renders."""
    return Path(os.environ.get("STUDIO_DATA_DIR") or DEFAULT_DATA_DIR).expanduser().resolve()


DEFAULT_RENDER_ROOT = DEFAULT_DATA_DIR / "renders"


class Render(Base):
    __tablename__ = "renders"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "product_id"],
            ["products.workspace_id", "products.id"],
            ondelete="CASCADE",
            name="fk_render_workspace_product",
        ),
        UniqueConstraint("workspace_id", "id", name="uq_renders_workspace_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="processing")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    video_relpath: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RenderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    product_id: str
    status: str
    created_at: datetime


def render_root() -> Path:
    return Path(os.environ.get("RENDER_ROOT") or data_dir() / "renders").expanduser().resolve()


def render_video_path(render: Render) -> Path:
    """Return an existing artifact only when its stored relative path stays in render root."""
    if render.video_relpath != f"{render.id}/preview.mp4":
        raise FileNotFoundError("render has no video artifact")
    root = render_root()
    path = (root / render.video_relpath).resolve()
    if root not in path.parents or path.suffix.lower() != ".mp4" or not path.is_file():
        raise FileNotFoundError("render video artifact is unavailable")
    return path


def _write_normalized_image(
    raw: bytes, content_type: str | None, path: Path, *, fit_full_image: bool = False,
) -> None:
    if content_type not in IMAGE_FORMATS or not raw or len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=422, detail="Images must be JPEG, PNG, or WebP and at most 12 MiB"
        )
    expected_format = IMAGE_FORMATS[content_type]
    try:
        with Image.open(BytesIO(raw)) as img:
            if img.width * img.height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=422, detail="Unsupported or oversized image")
            if img.format != expected_format:
                raise HTTPException(
                    status_code=422, detail="Image format does not match its content type"
                )
            if getattr(img, "is_animated", False):
                raise HTTPException(status_code=422, detail="Choose a still image")
            upright = ImageOps.exif_transpose(img)
            fit = ImageOps.contain if fit_full_image else ImageOps.fit
            fitted = fit(upright.convert("RGBA"), (1080, 1920), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (1080, 1920), "#101510" if fit_full_image else "white")
            position = ((canvas.width - fitted.width) // 2, (canvas.height - fitted.height) // 2)
            canvas.paste(fitted, position, fitted.getchannel("A"))
            canvas.save(path, format="PNG")
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=422, detail="Uploaded file is not a valid image") from None


def _write_scene_captions(scenes: list[str], path: Path, boundaries: list[float] | None = None) -> None:
    font = "Sukhumvit Set" if sys.platform == "darwin" else "Noto Sans Thai"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},52,&H00FFFFFF,&H00FFFFFF,&H30081419,&H30081419,-1,0,0,0,100,100,0,0,3,14,0,2,110,110,295,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    if boundaries is None:
        boundaries = [index * 5 for index in range(len(scenes) + 1)]
    for index, scene in enumerate(scenes):
        if not scene:
            continue
        # Only these server-defined timestamps and line breaks can change ASS formatting.
        lines = ["".join(char for char in line if char.isprintable()) for line in scene.splitlines()]
        escaped = r"\N".join(line.translate(str.maketrans("{}\\", "｛｝＼")) for line in lines)
        start, end = (math.floor(value * 100 + 1e-6) / 100 for value in boundaries[index:index + 2])
        events.append(f"Dialogue: 0,0:00:{start:05.2f},0:00:{end:05.2f},Caption,,0,0,0,,{escaped}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def _render(inputs: list[Path], output: Path, scenes: list[str] | None = None) -> None:
    script = Path(__file__).resolve().parents[2] / "spikes" / "phase0_video" / "render_sample.sh"
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and ffprobe are required on PATH")
    args = ["bash", str(script), *map(str, inputs), str(output)]
    if scenes is not None:
        _write_scene_captions(scenes, output.parent / "captions.ass")
        args.append("--captions")
    _run_render(args, output)


def _run_render(args: list[str], output: Path, *, expected_frames: int | None = None) -> None:
    with subprocess.Popen(
        args, cwd=output.parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
    ) as process:
        try:
            returncode = process.wait(timeout=RENDER_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
    if returncode:
        raise subprocess.CalledProcessError(returncode, args)
    if not output.is_file() or output.stat().st_size > 64 * 1024 * 1024:
        raise RuntimeError("FFmpeg output missing or exceeds 64 MiB")
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,sample_rate,channels,nb_frames",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    try:
        metadata = json.loads(result.stdout)
        video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        audio = next(s for s in metadata["streams"] if s["codec_type"] == "audio")
        duration = float(metadata["format"]["duration"])
        valid = (
            video["codec_name"] == "h264"
            and video["width"] == 1080
            and video["height"] == 1920
            and video["pix_fmt"] == "yuv420p"
            and video["r_frame_rate"] == "30/1"
            and audio["codec_name"] == "aac"
            and audio["sample_rate"] == "48000"
            and int(audio["channels"]) == 2
            and 14.8 <= duration <= 15.2
            and (expected_frames is None or int(video["nb_frames"]) == expected_frames)
        )
    except (KeyError, StopIteration, TypeError, ValueError):
        valid = False
    if not valid:
        raise RuntimeError("Rendered video does not match the 15-second MP4 preview spec")


def _clip_capacity(path: Path) -> int:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-protocol_whitelist", "file", "-f", "mov",
                "-show_entries", "stream=width,height,duration",
                "-select_streams", "V:0", "-of", "json", str(path),
            ],
            capture_output=True, text=True, timeout=15, check=True,
        )
        stream = json.loads(result.stdout)["streams"][0]
        width, height = int(stream["width"]), int(stream["height"])
        seconds = float(stream["duration"])
        if not 144 <= min(width, height) or max(width, height) > 4096 or not 1 <= seconds <= 120:
            raise ValueError("Clip dimensions or duration are out of range")
        return math.floor(seconds * FPS + 1e-6)
    except (subprocess.SubprocessError, IndexError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(422, "Use a playable MP4/MOV clip, 1–120 seconds and up to 4096 pixels") from exc


def _allocate_frames(capacities: list[int | None]) -> list[int]:
    limits = [REEL_FRAMES if cap is None else cap for cap in capacities]
    if sum(limits) < REEL_FRAMES:
        raise HTTPException(422, "Choose at least 15 seconds of footage in total or add product photos")
    weights = [1 if cap is None else 2 for cap in capacities]
    frames = [0] * len(limits)
    for _ in range(REEL_FRAMES):
        available = (index for index, limit in enumerate(limits) if frames[index] < limit)
        target = min(available, key=lambda index: (frames[index] / weights[index], index))
        frames[target] += 1
    return frames


def _render_media(
    inputs: list[Path], output: Path, shots: list[TimelineShot], scenes: list[str] | None,
) -> None:
    args = ["ffmpeg", "-v", "error", "-y", "-filter_complex_threads", "2"]
    filters = []
    for index, shot in enumerate(shots):
        path = inputs[shot.asset_index]
        length = shot.frames
        clip = path.suffix == ".mov"
        args.extend(["-threads", "2", "-protocol_whitelist", "file", "-f",
                     "mov" if clip else "png_pipe", "-i", str(path)])
        if clip:
            motion = (
                "scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x101510,fps=30,"
                f"tpad=stop_mode=clone:stop_duration=0.12,trim=start_frame={shot.start_frame}:end_frame={shot.start_frame + length}"
            )
        else:
            motion = f"loop=loop={length - 1}:size=1:start=0,trim=end_frame={length}"
        filters.append(f"[{index}:V:0]{motion},setsar=1,settb=1/{FPS},setpts=N,format=yuv420p[v{index}]")
    chain = "".join(f"[v{index}]" for index in range(len(shots)))
    chain += f"concat=n={len(shots)}:v=1:a=0,settb=1/{FPS},setpts=N"
    planned_subtitles = [shot.subtitle for shot in shots]
    if any(planned_subtitles):
        boundaries = [0.0, *(frame / FPS for frame in accumulate(shot.frames for shot in shots))]
        _write_scene_captions(planned_subtitles, output.parent / "captions.ass", boundaries)
        chain += ",ass=filename=captions.ass"
    elif scenes:
        _write_scene_captions(scenes, output.parent / "captions.ass")
        chain += ",ass=filename=captions.ass"
    filters.append(chain + "[out]")
    args.extend([
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-filter_complex", ";".join(filters), "-map", "[out]", "-map", f"{len(shots)}:a:0",
        "-c:v", "libx264", "-threads", "4", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-t", "15", "-movflags", "+faststart", str(output),
    ])
    _run_render(args, output, expected_frames=REEL_FRAMES)


def _media_type(upload: UploadFile) -> str | None:
    if upload.content_type not in (None, "application/octet-stream"):
        return upload.content_type
    suffix = Path(upload.filename or "").suffix.lower()
    return {".mp4": "video/mp4", ".mov": "video/quicktime"}.get(suffix)


def _prepare_media(raw: bytes, media_type: str | None, workdir: Path, index: int) -> tuple[Path, int | None]:
    if media_type in CLIP_TYPES:
        if not raw or len(raw) > MAX_CLIP_BYTES:
            raise HTTPException(422, "Each clip must be at most 48 MiB")
        path = workdir / f"clip-{index}.mov"
        path.write_bytes(raw)
        return path, _clip_capacity(path)
    path = workdir / f"image-{index}.png"
    _write_normalized_image(raw, media_type, path, fit_full_image=True)
    return path, None


@router.post("", response_model=RenderOut, status_code=status.HTTP_201_CREATED)
async def create_render(
    workspace_id: str,
    product_id: Annotated[str, Form()],
    db: Session = Depends(get_db),
    context=Depends(require_workspace),
    scene_texts: Annotated[list[str] | None, Form()] = None,
    images: Annotated[list[UploadFile] | None, File()] = None,
    media: Annotated[list[UploadFile] | None, File()] = None,
    reel_plan: Annotated[str | None, Form(max_length=32_768)] = None,
):
    if str(context.workspace_id) != str(workspace_id):
        raise HTTPException(404, "Workspace not found")
    plan = None
    if reel_plan:
        if media is None:
            raise HTTPException(422, "Upload the plan assets with the media field")
        try:
            plan = ReelPlan.model_validate_json(reel_plan)
        except ValidationError as exc:
            error = exc.errors(include_input=False)[0]
            field = ".".join(map(str, error["loc"]))
            raise HTTPException(422, f"Reel plan {field}: {error['msg']}") from exc
        scene_texts = None
    if media is not None:
        if images is not None or not 1 <= len(media) <= MAX_MEDIA_FILES:
            raise HTTPException(422, "Provide up to 12 media files in one upload format")
        if plan is None and not any(_media_type(upload) in CLIP_TYPES for upload in media) and len(media) < MIN_PHOTOS:
            raise HTTPException(422, "Choose a video clip or at least four product photos")
        uploads, total_limit = media, MAX_MEDIA_BYTES
    elif images is not None and len(images) == 3:
        uploads, total_limit = images, MAX_TOTAL_BYTES
    else:
        raise HTTPException(422, "Choose product media or provide three images for the legacy render")
    if scene_texts is not None:
        scene_texts = [scene.strip() for scene in scene_texts]
        if len(scene_texts) != 3 or any(
            not scene or len(scene) > SCENE_TEXT_LIMIT or len(scene.splitlines()) > 3
            or not any(char.isprintable() and not char.isspace() for char in scene)
            for scene in scene_texts
        ):
            raise HTTPException(422, "Enter three scene captions, up to 120 characters and three lines each")
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace_id)
    )
    if product is None:
        raise HTTPException(404, "Product not found")
    if not product.image_rights_note or not product.image_rights_note.strip():
        detail = "Document media usage rights before rendering" if media is not None else "Document image rights before rendering"
        raise HTTPException(422, detail)
    render_id = str(uuid.uuid4())
    root = render_root()
    workdir = root / render_id
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    workdir.mkdir(mode=0o700)
    paths = []
    capacities = []
    total = 0
    try:
        for ix, upload in enumerate(uploads):
            media_type = _media_type(upload) if media is not None else upload.content_type
            limit = MAX_CLIP_BYTES if media_type in CLIP_TYPES else MAX_IMAGE_BYTES
            raw = await upload.read(limit + 1)
            total += len(raw)
            if total > total_limit:
                raise HTTPException(422, f"Combined upload size exceeds {total_limit // (1024 * 1024)} MiB")
            if media is not None:
                path, capacity = await asyncio.to_thread(_prepare_media, raw, media_type, workdir, ix)
                capacities.append(capacity)
            else:
                path = workdir / f"image-{ix}.png"
                _write_normalized_image(raw, upload.content_type, path)
            paths.append(path)
        shots = None
        if plan is not None:
            try:
                shots = compile_timeline(plan, capacities)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
        elif media is not None:
            shots = [TimelineShot(index, length) for index, length in enumerate(_allocate_frames(capacities))]
        render = Render(
            id=render_id,
            workspace_id=workspace_id,
            product_id=product_id,
            status="processing",
            video_relpath=f"{render_id}/preview.mp4",
        )
        db.add(render)
        db.commit()
        try:
            output = workdir / "preview.mp4"
            if shots is None:
                await asyncio.to_thread(_render, paths, output, scene_texts)
            else:
                await asyncio.to_thread(_render_media, paths, output, shots, scene_texts)
            render.status = "completed"
        except (subprocess.SubprocessError, OSError, RuntimeError):
            render.status = "failed"
            render.error = "Video rendering or validation failed"
            (workdir / "preview.mp4").unlink(missing_ok=True)
        finally:
            for path in paths:
                path.unlink(missing_ok=True)
            (workdir / "captions.ass").unlink(missing_ok=True)
        db.commit()
        db.refresh(render)
        return render
    except Exception:
        db.rollback()
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    finally:
        for upload in uploads:
            await upload.close()


@router.get("", response_model=list[RenderOut])
def list_renders(
    workspace_id: str, db: Session = Depends(get_db), context=Depends(require_workspace)
):
    if str(context.workspace_id) != str(workspace_id):
        raise HTTPException(404, "Workspace not found")
    return list(
        db.scalars(
            select(Render)
            .where(Render.workspace_id == workspace_id)
            .order_by(Render.created_at.desc())
        ).all()
    )


@router.get("/{render_id}/video")
def get_render_video(
    workspace_id: str,
    render_id: str,
    db: Session = Depends(get_db),
    context=Depends(require_workspace),
):
    if str(context.workspace_id) != str(workspace_id):
        raise HTTPException(404, "Workspace not found")
    render = db.scalar(
        select(Render).where(Render.id == render_id, Render.workspace_id == workspace_id)
    )
    if render is None or render.status != "completed":
        raise HTTPException(404, "Render video not found")
    try:
        path = render_video_path(render)
    except FileNotFoundError:
        raise HTTPException(404, "Render video not found") from None
    return FileResponse(path, media_type="video/mp4", filename=f"{render.id}.mp4")
