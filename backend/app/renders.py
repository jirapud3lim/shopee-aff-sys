"""Bounded, local-only product video rendering for the Phase 3 vertical slice."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKeyConstraint, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .auth import require_workspace
from .db import Base, get_db
from .products import Product

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/renders", tags=["renders"])
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = 30 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
RENDER_TIMEOUT_SECONDS = 180
IMAGE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
DEFAULT_RENDER_ROOT = Path(__file__).resolve().parents[1] / ".local" / "renders"


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
    return Path(os.environ.get("RENDER_ROOT", str(DEFAULT_RENDER_ROOT))).expanduser().resolve()


def render_video_path(render: Render) -> Path:
    """Return an existing artifact only when its stored relative path stays in render root."""
    if render.video_relpath != f"{render.id}/preview.mp4":
        raise FileNotFoundError("render has no video artifact")
    root = render_root()
    path = (root / render.video_relpath).resolve()
    if root not in path.parents or path.suffix.lower() != ".mp4" or not path.is_file():
        raise FileNotFoundError("render video artifact is unavailable")
    return path


def _write_normalized_image(raw: bytes, content_type: str | None, path: Path) -> None:
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
            cropped = ImageOps.fit(upright.convert("RGBA"), (1080, 1920), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", cropped.size, "white")
            canvas.paste(cropped, mask=cropped.getchannel("A"))
            canvas.save(path, format="PNG")
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=422, detail="Uploaded file is not a valid image") from None


def _render(inputs: list[Path], output: Path) -> None:
    script = Path(__file__).resolve().parents[2] / "spikes" / "phase0_video" / "render_sample.sh"
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and ffprobe are required on PATH")
    args = ["bash", str(script), *map(str, inputs), str(output)]
    with subprocess.Popen(
        args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
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
            "stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,sample_rate,channels",
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
        )
    except (KeyError, StopIteration, TypeError, ValueError):
        valid = False
    if not valid:
        raise RuntimeError("Rendered video does not match the 15-second MP4 preview spec")


@router.post("", response_model=RenderOut, status_code=status.HTTP_201_CREATED)
async def create_render(
    workspace_id: str,
    product_id: Annotated[str, Form()],
    images: Annotated[list[UploadFile], File()],
    db: Session = Depends(get_db),
    context=Depends(require_workspace),
):
    if str(context.workspace_id) != str(workspace_id):
        raise HTTPException(404, "Workspace not found")
    if len(images) != 3:
        raise HTTPException(422, "Exactly three product images are required")
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.workspace_id == workspace_id)
    )
    if product is None:
        raise HTTPException(404, "Product not found")
    if not product.image_rights_note or not product.image_rights_note.strip():
        raise HTTPException(422, "Document image rights before rendering")
    render_id = str(uuid.uuid4())
    root = render_root()
    workdir = root / render_id
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    workdir.mkdir(mode=0o700)
    paths = []
    total = 0
    try:
        for ix, upload in enumerate(images):
            raw = await upload.read(MAX_IMAGE_BYTES + 1)
            total += len(raw)
            if total > MAX_TOTAL_BYTES:
                raise HTTPException(422, "Combined image size exceeds 30 MiB")
            path = workdir / f"image-{ix}.png"
            _write_normalized_image(raw, upload.content_type, path)
            paths.append(path)
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
            await asyncio.to_thread(_render, paths, workdir / "preview.mp4")
            render.status = "completed"
        except (subprocess.SubprocessError, OSError, RuntimeError):
            render.status = "failed"
            render.error = "Video rendering or validation failed"
            (workdir / "preview.mp4").unlink(missing_ok=True)
        finally:
            for path in paths:
                path.unlink(missing_ok=True)
        db.commit()
        db.refresh(render)
        return render
    except Exception:
        db.rollback()
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    finally:
        for upload in images:
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
