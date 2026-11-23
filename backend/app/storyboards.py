"""Workspace-scoped still storyboard packages for the Google Flow web workflow."""

import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from .auth import WorkspaceContext, require_workspace
from .db import get_db
from .products import Product
from .renders import render_root
from .shopee_offers import ShopeeOffer

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/storyboards", tags=["storyboards"])
Context = Annotated[WorkspaceContext, Depends(require_workspace)]
DB = Annotated[Session, Depends(get_db)]
Asset = Literal["product", "presenter", "board"]
MAX_IMAGE_BYTES = 12 * 1024 * 1024


class Scene(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    seconds: int = Field(ge=1, le=15)
    action: str = Field(min_length=1, max_length=500)
    dialogue: str = Field(max_length=300)


class Plan(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    source: Literal["offer", "catalog"]
    source_id: str = Field(min_length=1, max_length=36)
    variant: str = Field(min_length=1, max_length=180)
    verified_details: str = Field(min_length=1, max_length=600)
    scenes: list[Scene] = Field(min_length=1, max_length=12)


class Storyboard(Plan):
    id: UUID
    product_name: str
    created_at: datetime
    files: dict[Asset, str]


def workspace_path(context: WorkspaceContext) -> Path:
    return render_root() / "storyboards" / context.workspace_id


def load_board(folder: Path) -> Storyboard:
    manifest = folder / "plan.json"
    if not manifest.is_file():
        raise HTTPException(404, "ไม่พบ Storyboard")
    board = Storyboard.model_validate_json(manifest.read_bytes())
    if (folder / "board.img").is_file():
        board.files["board"] = "storyboard-from-flow" + image_suffix(folder / "board.img")
    return board


def image_suffix(path: Path) -> str:
    with Image.open(path, formats=["JPEG", "PNG", "WEBP"]) as image:
        return {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[image.format]


def save_image(upload: UploadFile, path: Path) -> str:
    payload = upload.file.read(MAX_IMAGE_BYTES + 1)
    if len(payload) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "ภาพแต่ละไฟล์ต้องมีขนาดไม่เกิน 12 MB")
    path.write_bytes(payload)
    try:
        with Image.open(path, formats=["JPEG", "PNG", "WEBP"]) as image:
            if image.width * image.height > 24_000_000 or getattr(image, "n_frames", 1) != 1:
                raise ValueError("Invalid image dimensions or frame count")
            image.verify()
        with Image.open(path, formats=["JPEG", "PNG", "WEBP"]) as image:
            image.load()
        return image_suffix(path)
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "ใช้ภาพนิ่ง JPG, PNG หรือ WebP ที่เปิดได้") from exc


@router.get("", response_model=list[Storyboard])
def list_storyboards(context: Context):
    root = workspace_path(context)
    if not root.is_dir():
        return []
    folders = [file.parent for file in root.glob("*/plan.json")]
    return [load_board(folder) for folder in sorted(
        folders, key=lambda folder: (folder / "plan.json").stat().st_mtime_ns, reverse=True,
    )]


@router.post("", response_model=Storyboard, status_code=201)
def create_storyboard(
    context: Context, db: DB, plan: Annotated[str, Form()],
    product: Annotated[UploadFile, File()], presenter: Annotated[UploadFile, File()],
):
    try:
        data = Plan.model_validate_json(plan)
    except ValidationError as exc:
        raise HTTPException(422, "ตรวจรุ่นสินค้า รายละเอียดที่ยืนยันแล้ว และแผนรายฉาก") from exc

    workspace = context.workspace_id
    selected = (db.get(ShopeeOffer, (workspace, data.source_id)) if data.source == "offer"
                else db.get(Product, data.source_id))
    if selected is None or selected.workspace_id != workspace:
        raise HTTPException(404, "ไม่พบสินค้าในพื้นที่ทำงานนี้")

    root = workspace_path(context)
    root.mkdir(parents=True, exist_ok=True)
    storyboard_id = uuid4()
    with TemporaryDirectory(dir=root) as temp:
        staging = Path(temp) / "draft"
        staging.mkdir()
        files = {
            "product": "product-reference" + save_image(product, staging / "product.img"),
            "presenter": "presenter-reference" + save_image(presenter, staging / "presenter.img"),
        }
        board = Storyboard(
            **data.model_dump(), id=storyboard_id, product_name=selected.name,
            created_at=datetime.now(UTC), files=files,
        )
        (staging / "plan.json").write_text(board.model_dump_json(), encoding="utf-8")
        staging.rename(root / str(storyboard_id))
    return board


@router.put("/{storyboard_id}/image", response_model=Storyboard)
def import_board(storyboard_id: UUID, context: Context, image: Annotated[UploadFile, File()]):
    folder = workspace_path(context) / str(storyboard_id)
    load_board(folder)
    with TemporaryDirectory(dir=folder) as temp:
        staged = Path(temp) / "board.img"
        save_image(image, staged)
        os.replace(staged, folder / "board.img")
    return load_board(folder)


@router.get("/{storyboard_id}/files/{asset}")
def get_asset(storyboard_id: UUID, asset: Asset, context: Context):
    folder = workspace_path(context) / str(storyboard_id)
    name = load_board(folder).files.get(asset)
    if not name:
        raise HTTPException(404, "ไม่พบไฟล์ภาพ")
    return FileResponse(
        folder / f"{asset}.img", filename=name, content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
