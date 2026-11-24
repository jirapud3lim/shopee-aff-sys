"""Local asset collection and preview-only renders for confirmed purchases."""

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Annotated, Literal
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, HttpUrl

from app.content.flow_preview import MAX_FLOW_BYTES, render_flow_preview
from app.content.renders import (
    IMAGE_FORMATS,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_PIXELS,
    _render,
    render_root,
)
from app.core.auth import WorkspaceContext, require_workspace

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/purchase-previews", tags=["purchase previews"])
Context = Annotated[WorkspaceContext, Depends(require_workspace)]
PRODUCT_KEY = re.compile(r"shopee-[0-9]{1,20}-[0-9]{1,20}")
PRODUCT_PATH = re.compile(r"/product/([0-9]{1,20})/([0-9]{1,20})/?")
PRODUCT_SLUG = re.compile(r"/[^/]+-i\.([0-9]{1,20})\.([0-9]{1,20})/?")
SOURCE_HOSTS = {
    "shopee": {"down-th.img.susercontent.com": "/file/"},
    "google": {
        "www.potterscookshop.co.uk": "/cdn/shop/files/",
        "cdn.hstatic.net": "/products/",
        "www.electronic4you.at": "/media/catalog/product/",
        "assets.4flow.cloud": "/WBF",
        "vc3i.rweb-images.com": "/www.light-and-bath.com/images/catalog_images/",
    },
}


class PurchaseInput(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=140)]
    product_url: HttpUrl
    shopee_image: HttpUrl
    search_images: Annotated[list[HttpUrl], Field(min_length=2, max_length=2)]
    purchase_confirmed: bool
    scene_crops: tuple[tuple[float, float, float, float] | None, ...] | None = None


class CollectedPurchase(PurchaseInput):
    purchase_source: Literal["shopee_completed"]
    search_source: Literal["google_images"]


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        return None


def asset_root(workspace: str) -> Path:
    return render_root() / "Asset" / workspace


def product_dir(workspace: str, key: str) -> Path:
    if not PRODUCT_KEY.fullmatch(key):
        raise HTTPException(404, "Purchase not found")
    return asset_root(workspace) / key


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def write_json(path: Path, data) -> None:
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        try:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


def safe_url(url: str, hosts: dict[str, str]):
    parsed = urlsplit(url)
    prefix = hosts.get(parsed.hostname or "")
    if (parsed.scheme != "https" or prefix is None or not parsed.path.startswith(prefix)
            or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443)):
        raise HTTPException(422, "ใช้ URL รูปโดยตรงจากแหล่งที่ Studio รองรับ")
    return parsed


def fetch_image(url: str, source: str) -> tuple[bytes, Image.Image, str]:
    safe_url(url, SOURCE_HOSTS[source])
    request = Request(url, headers={"Accept": "image/jpeg, image/png, image/webp", "User-Agent": "AffiliateStudio/1.0"})
    with build_opener(NoRedirects()).open(request, timeout=12) as response:
        content_type = response.headers.get_content_type()
        raw = response.read(MAX_IMAGE_BYTES + 1)
    if content_type not in IMAGE_FORMATS or not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Invalid image response")
    with Image.open(BytesIO(raw)) as image:
        if (image.format != IMAGE_FORMATS[content_type] or getattr(image, "is_animated", False)
                or image.width * image.height > MAX_IMAGE_PIXELS or min(image.size) < 300):
            raise ValueError("Unsupported image")
        fitted = ImageOps.exif_transpose(image).convert("RGBA")
    return raw, fitted, {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]


def purchase_record(directory: Path):
    record = read_json(directory / "purchase.json")
    if record is None:
        raise HTTPException(404, "Purchase not found")
    return record


def preview_info(directory: Path):
    data = read_json(directory / "preview.json")
    if data is not None and (directory / "runs" / data["id"] / "preview.mp4").is_file():
        return data
    return None


@router.get("")
def list_purchases(context: Context):
    root = asset_root(context.workspace_id)
    purchases = []
    for path in sorted(root.glob("shopee-*/purchase.json")):
        purchase = read_json(path)
        purchases.append({**purchase, "preview": preview_info(path.parent)})
    return purchases


@router.post("")
def register_purchase(body: PurchaseInput, context: Context):
    return save_purchase(body, context.workspace_id)


def save_purchase(body: PurchaseInput, workspace: str):
    name = body.name.strip()
    if not body.purchase_confirmed or not name:
        raise HTTPException(422, "ยืนยันว่าคำสั่งซื้อสำเร็จก่อนเพิ่มรายการ")
    product = safe_url(str(body.product_url), {"shopee.co.th": "/", "www.shopee.co.th": "/"})
    ids = PRODUCT_PATH.fullmatch(product.path) or PRODUCT_SLUG.fullmatch(product.path)
    if ids is None:
        raise HTTPException(422, "ใช้ลิงก์หน้าสินค้า Shopee ที่ระบุร้านและรหัสสินค้า")
    key = f"shopee-{ids[1]}-{ids[2]}"
    urls = {"shopee": [str(body.shopee_image)], "google": [str(url) for url in body.search_images]}
    if len(set(urls["shopee"] + urls["google"])) != 3:
        raise HTTPException(422, "ใช้รูปสามภาพที่แตกต่างกัน")
    for source, links in urls.items():
        for url in links:
            safe_url(url, SOURCE_HOSTS[source])
    crops = body.scene_crops
    if crops is not None and (len(crops) != 3 or not all(
        0 <= left < right <= 1 and 0 <= top < bottom <= 1
        and right - left >= .15 and bottom - top >= .15
        for left, top, right, bottom in (crop for crop in crops if crop is not None)
    )):
        raise HTTPException(422, "กรอบภาพต้องอยู่ภายในภาพต้นฉบับทั้งสามรูป")
    directory = product_dir(workspace, key)
    directory.mkdir(parents=True, exist_ok=True)
    record = {"id": key, "name": name, "product_url": f"https://shopee.co.th/product/{ids[1]}/{ids[2]}",
              "sources": urls, "purchase_status": "confirmed_completed"}
    if crops is not None:
        record["scene_crops"] = crops
    if isinstance(body, CollectedPurchase):
        record["purchase_source"] = body.purchase_source
        record["search_source"] = body.search_source
    write_json(directory / "purchase.json", record)
    return {**record, "preview": preview_info(directory)}


def frame_image(image: Image.Image, dest: Path, crop=None, cover: bool = False) -> None:
    canvas = Image.new("RGB", (1080, 1920), "#ffffff")
    if crop is not None:
        width, height = image.size
        left, top, right, bottom = crop
        image = image.crop((round(left * width), round(top * height),
                            round(right * width), round(bottom * height)))
    if cover:
        photo = ImageOps.fit(image, canvas.size, Image.Resampling.LANCZOS)
        canvas.paste(photo, (0, 0), photo)
    else:
        photo = ImageOps.contain(image, (860, 1180), Image.Resampling.LANCZOS)
        canvas.paste(photo, ((1080 - photo.width) // 2, (1630 - photo.height) // 2), photo)
    canvas.save(dest, format="PNG")


@router.post("/{key}/render")
def build_preview(key: str, context: Context):
    return render_purchase(key, context.workspace_id)


@router.post("/collect-and-render")
def collect_and_render(body: CollectedPurchase, context: Context):
    purchase = save_purchase(body, context.workspace_id)
    return {**purchase, "preview": render_purchase(purchase["id"], context.workspace_id)}


def render_purchase(key: str, workspace: str):
    directory = product_dir(workspace, key)
    record = purchase_record(directory)
    with TemporaryDirectory(dir=directory, prefix=".build-") as path:
        work = Path(path)
        output = work / "output"
        output.mkdir()
        inputs, saved, fingerprints = [], [], set()
        # Start with a setting photo, then show the listing photo and a closer detail.
        specs = [("google", record["sources"]["google"][0]), ("shopee", record["sources"]["shopee"][0]),
                 ("google", record["sources"]["google"][1])]
        for index, (source, url) in enumerate(specs, 1):
            try:
                raw, image, extension = fetch_image(url, source)
                fingerprint = hashlib.sha256(raw).digest()
                if fingerprint in fingerprints:
                    raise ValueError("Duplicate image")
                fingerprints.add(fingerprint)
                relative = f"{source}/photo-{index}.{extension}"
                original = output / relative
                original.parent.mkdir(exist_ok=True)
                original.write_bytes(raw)
                frame = work / f"frame-{index}.png"
                crops = record.get("scene_crops")
                crop = crops[index - 1] if crops else None
                frame_image(image, frame, crop, cover=crop is not None and index == 1)
                inputs.append(frame)
                saved.append({"source": source, "url": url, "file": relative,
                              "width": image.width, "height": image.height,
                              "publication_rights": "unverified"})
            except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
                raise HTTPException(422, f"เก็บภาพลำดับ {index} ไม่สำเร็จ ตรวจสอบ URL และรูปต้นฉบับ") from exc
        short_name = record["name"][:76]
        try:
            _render(inputs, output / "preview.mp4", [
                "ของใช้ที่น่าสนใจ", short_name, "ดูรายละเอียดจากหน้าสินค้า",
            ])
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            raise HTTPException(500, "FFmpeg สร้างตัวอย่างไม่สำเร็จ") from exc
        return save_preview(directory, output, saved)


def save_preview(directory: Path, output: Path, saved: list, **details):
    (output / "captions.ass").unlink(missing_ok=True)
    run_id = str(uuid4())
    runs = directory / "runs"
    runs.mkdir(exist_ok=True)
    result = {"id": run_id, "generated_at": datetime.now(timezone.utc).isoformat(),
              "assets": saved, "seconds": 15, **details}
    write_json(output / "sources.json", result)
    output.rename(runs / run_id)
    write_json(directory / "preview.json", result)
    return result


@router.post("/{key}/flow-preview")
def build_flow_preview(
    key: str, context: Context, clip: Annotated[UploadFile, File()],
    opening_text: Annotated[str, Form(max_length=70)] = "",
    product_first: Annotated[bool, Form()] = False,
):
    directory = product_dir(context.workspace_id, key)
    record = purchase_record(directory)
    previous = preview_info(directory)
    if previous is None or len(previous["assets"]) < 2:
        raise HTTPException(409, "เก็บภาพสินค้าสำหรับตัวอย่างก่อนนำเข้า MP4 จาก Flow")
    if not (clip.filename or "").lower().endswith(".mp4"):
        raise HTTPException(422, "เลือกไฟล์ MP4 จาก Google Flow")

    with TemporaryDirectory(dir=directory, prefix=".flow-") as path:
        work = Path(path)
        output = work / "output"
        output.mkdir()
        opener = output / "flow-opening.mp4"
        with opener.open("wb") as destination:
            total = 0
            while data := clip.file.read(1024 * 1024):
                total += len(data)
                if total > MAX_FLOW_BYTES:
                    raise HTTPException(413, "ไฟล์ MP4 ต้องมีขนาดไม่เกิน 48 MiB")
                destination.write(data)
        assets = previous["assets"][:3 if product_first else 2]
        photos = []
        for index, asset in enumerate(assets):
            relative = asset["file"]
            if not re.fullmatch(r"(?:google|shopee)/photo-[123]\.(?:jpg|png|webp)", relative):
                raise HTTPException(409, "โครงสร้างไฟล์ภาพเดิมไม่ตรงกับตัวอย่าง")
            original = directory / "runs" / previous["id"] / relative
            saved = output / relative
            saved.parent.mkdir(exist_ok=True)
            photo = work / f"photo-{index}.png"
            crops = record.get("scene_crops")
            crop = crops[index] if crops else None
            try:
                with Image.open(original) as image:
                    upright = ImageOps.exif_transpose(image).convert("RGBA")
                frame_image(upright, photo, crop, cover=index == 0 and crop is not None)
                shutil.copyfile(original, saved)
            except (OSError, UnidentifiedImageError) as exc:
                raise HTTPException(409, "ภาพต้นฉบับไม่ครบ กรุณาเก็บภาพใหม่ใน Studio") from exc
            photos.append(photo)
        try:
            opening = render_flow_preview(
                opener, photos, output / "preview.mp4", record["name"][:76], opening_text.strip(),
                product_first=product_first,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            raise HTTPException(500, "FFmpeg ต่อช็อตเปิดกับภาพสินค้าไม่สำเร็จ") from exc
        timing = {"source": "google_flow", "file": opener.name, "seconds": opening,
                  "text": opening_text.strip()}
        if product_first:
            timing["starts_at"] = 4
        return save_preview(directory, output, assets, opening=timing)


@router.get("/{key}/video/{run_id}")
def preview_video(key: str, run_id: UUID, context: Context):
    directory = product_dir(context.workspace_id, key)
    video = directory / "runs" / str(run_id) / "preview.mp4"
    if not video.is_file():
        raise HTTPException(404, "Preview not found")
    return FileResponse(video, media_type="video/mp4", headers={"Cache-Control": "private, no-store"})
