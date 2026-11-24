"""Tenant-scoped product library endpoints (manual and CSV ingest only).

No product pages are fetched here. Source and affiliate URLs are supplied by
the workspace user; image rights are recorded for downstream render checks.
"""

from __future__ import annotations

import csv
import io
import uuid
from typing import Annotated, Any
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, Text, UniqueConstraint, null, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .auth import require_workspace
from .db import Base, get_db

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/products", tags=["products"])

MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_CSV_ROWS = 1000


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source_url", name="uq_products_workspace_source_url"),
        UniqueConstraint("workspace_id", "id", name="uq_products_workspace_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    affiliate_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_rights_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChannelLink(Base):
    __tablename__ = "product_channel_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "product_id"],
            ["products.workspace_id", "products.id"],
            ondelete="CASCADE",
        ),
    )

    workspace_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    channel: Mapped[str] = mapped_column(String(48), primary_key=True)
    affiliate_url: Mapped[str] = mapped_column(Text)
    sub_id: Mapped[str | None] = mapped_column(String(100))
    shopee_verification: Mapped[str | None] = mapped_column(String(16))
    shopee_verified_by: Mapped[str | None] = mapped_column(String(36))


Channel = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,47}$")]


class ChannelLinkInput(BaseModel):
    affiliate_url: HttpUrl
    sub_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]+$", max_length=100)

    @field_validator("affiliate_url")
    @classmethod
    def reject_credentials(cls, value: HttpUrl) -> HttpUrl:
        if value.username is not None or value.password is not None:
            raise ValueError("Affiliate links cannot contain credentials")
        return value


class ChannelLinkOut(ChannelLinkInput):
    model_config = ConfigDict(from_attributes=True)
    channel: Channel


class ChannelLinkReview(ChannelLinkOut):
    shopee_verification: str | None = None


class WorkspaceAffiliateLink(BaseModel):
    product_id: str
    product_name: str
    channel: str | None
    sub_id: str | None
    affiliate_url: str


def canonical_source_url(value: str) -> str:
    """Normalize URL identity conservatively while retaining query parameters."""
    parts = urlsplit(value.strip())
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    if not scheme or not hostname:
        raise ValueError("source_url must be an absolute HTTP or HTTPS URL")
    if scheme not in {"http", "https"}:
        raise ValueError("source_url must use HTTP or HTTPS")
    port = parts.port
    if parts.username is not None or parts.password is not None:
        raise ValueError("Product URLs cannot contain embedded credentials")
    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc += f":{port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


class ProductInput(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    source_url: HttpUrl
    affiliate_url: HttpUrl | None = None
    image_rights_note: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value


class ProductPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=300)
    source_url: HttpUrl | None = None
    affiliate_url: HttpUrl | None = None
    image_rights_note: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    source_url: str
    affiliate_url: str | None
    image_rights_note: str | None

    @classmethod
    def from_product(cls, product: Product) -> "ProductOut":
        return cls.model_validate(product, from_attributes=True)


def _workspace_id(context: Any) -> str:
    return str(context.workspace_id)


def _source_url(value: HttpUrl) -> str:
    try:
        return canonical_source_url(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _record(data: ProductInput, workspace_id: str) -> Product:
    return Product(
        workspace_id=workspace_id,
        name=data.name,
        source_url=_source_url(data.source_url),
        affiliate_url=str(data.affiliate_url) if data.affiliate_url else None,
        image_rights_note=data.image_rights_note,
    )


def _duplicate_error() -> HTTPException:
    return HTTPException(
        status_code=409, detail="A product with this source_url already exists in this workspace"
    )


@router.get("", response_model=list[ProductOut])
def list_products(
    workspace_id: str,
    context: Any = Depends(require_workspace),
    db: Session = Depends(get_db),
) -> list[ProductOut]:
    tenant_id = _workspace_id(context)
    rows = db.scalars(
        select(Product).where(Product.workspace_id == tenant_id).order_by(Product.name, Product.id)
    ).all()
    return [ProductOut.from_product(row) for row in rows]


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    workspace_id: str,
    payload: ProductInput,
    context: Any = Depends(require_workspace),
    db: Session = Depends(get_db),
) -> ProductOut:
    product = _record(payload, _workspace_id(context))
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_error() from exc
    db.refresh(product)
    return ProductOut.from_product(product)


@router.get("/affiliate-links", response_model=list[WorkspaceAffiliateLink])
def list_affiliate_links(
    workspace_id: str,
    context: Any = Depends(require_workspace),
    db: Session = Depends(get_db),
):
    workspace = _workspace_id(context)
    product = (Product.id.label("product_id"), Product.name.label("product_name"))
    channel_links = (
        select(*product, ChannelLink.channel, ChannelLink.sub_id, ChannelLink.affiliate_url)
        .join_from(Product, ChannelLink)
        .where(Product.workspace_id == workspace)
    )
    fallback_links = select(
        *product, null().label("channel"), null().label("sub_id"), Product.affiliate_url,
    ).where(Product.workspace_id == workspace, Product.affiliate_url.is_not(None))
    links = channel_links.union_all(fallback_links).subquery()
    return db.execute(select(links).order_by(
        links.c.product_name, links.c.product_id, links.c.channel.asc().nulls_last(),
    )).mappings().all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    workspace_id: str,
    product_id: str,
    context: Any = Depends(require_workspace),
    db: Session = Depends(get_db),
) -> ProductOut:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id, Product.workspace_id == _workspace_id(context)
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut.from_product(product)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    workspace_id: str,
    product_id: str,
    payload: ProductPatch,
    context: Any = Depends(require_workspace),
    db: Session = Depends(get_db),
) -> ProductOut:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id, Product.workspace_id == _workspace_id(context)
        ).with_for_update()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = payload.model_dump(exclude_unset=True)
    for required_field in ("name", "source_url"):
        if required_field in updates and updates[required_field] is None:
            raise HTTPException(status_code=422, detail=f"{required_field} cannot be null")
    if "source_url" in updates:
        updates["source_url"] = _source_url(updates["source_url"])
        if updates["source_url"] != product.source_url:
            db.execute(update(ChannelLink).where(
                ChannelLink.workspace_id == product.workspace_id, ChannelLink.product_id == product.id,
            ).values(shopee_verification=None, shopee_verified_by=None))
    if "affiliate_url" in updates and updates["affiliate_url"] is not None:
        updates["affiliate_url"] = str(updates["affiliate_url"])
    for key, value in updates.items():
        setattr(product, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_error() from exc
    db.refresh(product)
    return ProductOut.from_product(product)


@router.get("/{product_id}/channel-links", response_model=list[ChannelLinkOut])
def list_channel_links(
    product_id: str, context: Any = Depends(require_workspace), db: Session = Depends(get_db)
):
    workspace = _workspace_id(context)
    if not db.scalar(
        select(Product.id).where(Product.id == product_id, Product.workspace_id == workspace)
    ):
        raise HTTPException(404, "Product not found")
    return db.scalars(
        select(ChannelLink)
        .where(ChannelLink.workspace_id == workspace, ChannelLink.product_id == product_id)
        .order_by(ChannelLink.channel)
    ).all()


@router.put("/{product_id}/channel-links/{channel}", response_model=ChannelLinkOut)
def save_channel_link(
    product_id: str,
    channel: Channel,
    body: ChannelLinkInput,
    context: Any = Depends(require_workspace),
    db: Session = Depends(get_db),
):
    return persist_channel_link(product_id, channel, body, context, db)


def persist_channel_link(product_id, channel, body, context, db, *, shopee_verification=None):
    workspace = _workspace_id(context)
    if not db.scalar(
        select(Product.id).where(Product.id == product_id, Product.workspace_id == workspace)
    ):
        raise HTTPException(404, "Product not found")
    key = (workspace, product_id, channel)
    link = db.get(ChannelLink, key)
    if link is None:
        link = ChannelLink(workspace_id=workspace, product_id=product_id, channel=channel)
        db.add(link)
    if (link.affiliate_url, link.sub_id) != (str(body.affiliate_url), body.sub_id):
        link.shopee_verification = None
        link.shopee_verified_by = None
    if shopee_verification is not None and not link.shopee_verified_by:
        link.shopee_verification = shopee_verification
    link.affiliate_url = str(body.affiliate_url)
    link.sub_id = body.sub_id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Channel link changed concurrently. Retry saving.") from exc
    return link


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_products(
    workspace_id: str,
    file: Annotated[UploadFile, File(...)],
    context: Any = Depends(require_workspace),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Import CSV with columns name, source_url, affiliate_url, image_rights_note."""
    if file.content_type not in {
        "text/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }:
        raise HTTPException(status_code=415, detail="Upload a CSV file")
    content = await file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail=f"CSV exceeds {MAX_CSV_BYTES} bytes")
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        headers = {h.strip() for h in (reader.fieldnames or []) if h}
        if not {"name", "source_url"}.issubset(headers):
            raise HTTPException(
                status_code=422, detail="CSV headers must include name and source_url"
            )
        rows = []
        for row in reader:
            rows.append((reader.line_num, row))
            if len(rows) > MAX_CSV_ROWS:
                raise HTTPException(status_code=413, detail=f"CSV exceeds {MAX_CSV_ROWS} data rows")
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail="Malformed CSV") from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV must be UTF-8 encoded") from exc

    tenant_id = _workspace_id(context)
    imported = 0
    errors: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row_number, raw in rows:
        if None in raw:
            errors.append({"row": row_number, "error": "Unexpected extra column"})
            continue
        row = {(key or "").strip(): (value or "").strip() for key, value in raw.items()}
        try:
            data = ProductInput.model_validate(
                {
                    "name": row.get("name"),
                    "source_url": row.get("source_url"),
                    "affiliate_url": row.get("affiliate_url") or None,
                    "image_rights_note": row.get("image_rights_note") or None,
                }
            )
            channel = row.get("affiliate_channel")
            sub_id = row.get("affiliate_sub_id") or None
            channel_link = None
            if channel:
                channel = TypeAdapter(Channel).validate_python(channel)
                channel_link = ChannelLinkInput(affiliate_url=data.affiliate_url, sub_id=sub_id)
                data.affiliate_url = None
            elif sub_id:
                raise HTTPException(
                    422, "affiliate_channel is required when affiliate_sub_id is set"
                )
            product = _record(data, tenant_id)
            if product.source_url in seen:
                duplicates.append(
                    {
                        "row": row_number,
                        "source_url": product.source_url,
                        "reason": "duplicate in upload",
                    }
                )
                continue
            seen.add(product.source_url)
            exists = db.scalar(
                select(Product.id).where(
                    Product.workspace_id == tenant_id, Product.source_url == product.source_url
                )
            )
            if exists:
                duplicates.append(
                    {
                        "row": row_number,
                        "source_url": product.source_url,
                        "reason": "already exists",
                    }
                )
                continue
            try:
                with db.begin_nested():
                    db.add(product)
                    db.flush()
                    if channel_link:
                        db.add(
                            ChannelLink(
                                workspace_id=tenant_id,
                                product_id=product.id,
                                channel=channel,
                                affiliate_url=str(channel_link.affiliate_url),
                                sub_id=channel_link.sub_id,
                            )
                        )
            except IntegrityError:
                exists = db.scalar(
                    select(Product.id).where(
                        Product.workspace_id == tenant_id, Product.source_url == product.source_url
                    )
                )
                if not exists:
                    raise
                duplicates.append(
                    {
                        "row": row_number,
                        "source_url": product.source_url,
                        "reason": "already exists",
                    }
                )
            else:
                imported += 1
        except ValidationError as exc:
            messages = [
                f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in exc.errors()
            ]
            errors.append({"row": row_number, "error": "; ".join(messages)[:300]})
        except HTTPException as exc:
            errors.append({"row": row_number, "error": str(exc.detail)})
    db.commit()
    return {
        "imported": imported,
        "duplicates": duplicates,
        "errors": errors,
        "total_rows": len(rows),
    }
