"""Workspace-scoped automatic Shopee links and recorded operator review."""

import re
from typing import Annotated
from urllib.parse import parse_qs, urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import WorkspaceContext, require_workspace
from .config import Settings, get_settings
from .db import get_db
from .products import Channel, ChannelLink, ChannelLinkInput, ChannelLinkReview, Product, list_channel_links, persist_channel_link
from .shopee_affiliate import ShopeeError, generate_short_link, listing_identity, partner_tracking_link, verify_destination

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/shopee-links", tags=["shopee affiliate"])
Context = Annotated[WorkspaceContext, Depends(require_workspace)]
DB = Annotated[Session, Depends(get_db)]
Config = Annotated[Settings, Depends(get_settings)]


class GenerateInput(BaseModel):
    sub_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9]+$", max_length=100)]


def generation_mode(context, settings):
    if context.role != "owner" or context.workspace_id != settings.shopee_affiliate_workspace_id:
        return None
    if re.fullmatch(r"[0-9]{1,32}", settings.shopee_affiliate_partner_id):
        return "partner"
    if (re.fullmatch(r"[0-9]{1,32}", settings.shopee_affiliate_app_id)
            and settings.shopee_affiliate_secret.get_secret_value()):
        return "api"
    return None


def find_product(db, context, product_id, *, lock=False):
    query = select(Product).where(Product.workspace_id == context.workspace_id, Product.id == product_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    product = db.scalar(query)
    if product is None:
        raise HTTPException(404, "ไม่พบสินค้าในพื้นที่ทำงานนี้")
    return product


def destination_status(url, identity, sub_id):
    status = verify_destination(url, identity, sub_id)
    if status == "mismatch":
        raise HTTPException(422, "ลิงก์ Affiliate เปิดคนละรายการสินค้า หรือ Sub ID ไม่ตรงกับช่องทางที่เลือก")
    return status


def check_sub_id(db, workspace, channel, sub_id):
    if sub_id and db.scalar(select(ChannelLink.channel).where(
        ChannelLink.workspace_id == workspace, ChannelLink.channel != channel,
        func.lower(ChannelLink.sub_id) == sub_id.lower(),
    ).limit(1)):
        raise HTTPException(409, "Sub ID นี้ใช้กับช่องทางอื่นแล้ว กรุณาใช้ Sub ID ของช่องทางนี้")


def affiliate_url(body):
    parts = body.affiliate_url
    url = str(parts)
    tracking = parse_qs(urlsplit(url).query)
    if (parts.scheme != "https" or parts.port not in (None, 443)
            or not (parts.host == "shopee.co.th" or (parts.host or "").endswith(".shopee.co.th"))
            or (parts.host or "").startswith("affiliate.") or parts.path in (None, "/")
            or (listing_identity(url) is not None and not {"utm_source", "uls_trackid"} & tracking.keys())):
        raise HTTPException(422, "ใช้ลิงก์ Affiliate ภาษาไทยที่สร้างจาก Shopee")
    return url


@router.get("")
def capabilities(context: Context, settings: Config):
    mode = generation_mode(context, settings)
    return {"generate_enabled": mode is not None, **({"mode": mode} if mode == "partner" else {})}


@router.get("/{product_id}", response_model=list[ChannelLinkReview])
def product_links(product_id: str, context: Context, db: DB):
    return list_channel_links(product_id, context, db)


@router.post("/{product_id}/{channel}", response_model=ChannelLinkReview)
def generate(product_id: str, channel: Channel, body: GenerateInput, context: Context, db: DB, settings: Config):
    mode = generation_mode(context, settings)
    if mode is None:
        raise HTTPException(403, "พื้นที่ทำงานนี้ยังไม่ได้ตั้งค่าการสร้างลิงก์อัตโนมัติ ใช้ลิงก์ที่สร้างจาก Shopee ได้")
    product = find_product(db, context, product_id)
    identity = listing_identity(product.source_url)
    if identity is None:
        raise HTTPException(422, "ใช้ URL หน้าสินค้า Shopee ที่มี Shop ID และ Item ID")
    key = (context.workspace_id, product_id, channel)
    existing = db.get(ChannelLink, key)
    if existing is not None:
        if existing.sub_id != body.sub_id:
            raise HTTPException(409, "มีลิงก์ช่องทางนี้แล้ว กรุณาเปิดดูและตรวจลิงก์เดิม")
        return existing
    check_sub_id(db, context.workspace_id, channel, body.sub_id)
    source_url = product.source_url
    db.rollback()
    listing = f"https://shopee.co.th/product/{identity[0]}/{identity[1]}"
    if mode == "partner":
        url = partner_tracking_link(listing, settings.shopee_affiliate_partner_id, body.sub_id)
    else:
        try:
            url = generate_short_link(settings, listing, body.sub_id)
        except ShopeeError:
            raise HTTPException(502, "Shopee Open API ยังสร้างลิงก์ไม่ได้ ลองสร้างใน Shopee แล้ววางกลับ") from None
    status = destination_status(url, identity, body.sub_id)
    if find_product(db, context, product_id, lock=True).source_url != source_url:
        raise HTTPException(409, "รายการสินค้าเปลี่ยนแล้ว กรุณาเลือกสินค้าอีกครั้ง")
    check_sub_id(db, context.workspace_id, channel, body.sub_id)
    link = ChannelLink(workspace_id=context.workspace_id, product_id=product_id, channel=channel,
                       affiliate_url=url, sub_id=body.sub_id, shopee_verification=status)
    db.add(link)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.get(ChannelLink, key)
        if existing is not None and existing.sub_id == body.sub_id:
            return existing
        raise HTTPException(409, "ลิงก์ของช่องทางเปลี่ยนแล้ว กรุณาเปิดดูใหม่") from None
    return link


@router.post("/{product_id}/{channel}/review", response_model=ChannelLinkReview)
def review(product_id: str, channel: Channel, body: ChannelLinkInput, context: Context, db: DB):
    product = find_product(db, context, product_id)
    identity = listing_identity(product.source_url)
    if identity is None:
        raise HTTPException(422, "รายการสินค้าไม่มี Shop ID และ Item ID ที่ตรวจได้")
    key = (context.workspace_id, product_id, channel)
    link = db.get(ChannelLink, key)
    expected = (affiliate_url(body), body.sub_id)
    if link is None or (link.affiliate_url, link.sub_id) != expected:
        raise HTTPException(409, "ลิงก์ของช่องทางเปลี่ยนแล้ว กรุณาเปิดดูใหม่")
    check_sub_id(db, context.workspace_id, channel, body.sub_id)
    if link.shopee_verified_by:
        return link
    db.rollback()
    status = destination_status(expected[0], identity, body.sub_id)
    if listing_identity(find_product(db, context, product_id, lock=True).source_url) != identity:
        raise HTTPException(409, "รายการสินค้าเปลี่ยนแล้ว กรุณาเลือกสินค้าอีกครั้ง")
    check_sub_id(db, context.workspace_id, channel, body.sub_id)
    link = db.get(ChannelLink, key, populate_existing=True, with_for_update=True)
    if link is None or (link.affiliate_url, link.sub_id) != expected:
        raise HTTPException(409, "ลิงก์ของช่องทางเปลี่ยนแล้ว กรุณาเปิดดูใหม่")
    link.shopee_verification = "manual" if status == "pending" else status
    link.shopee_verified_by = context.user_id
    db.commit()
    return link


@router.put("/{product_id}/{channel}", response_model=ChannelLinkReview)
def save_manual(product_id: str, channel: Channel, body: ChannelLinkInput, context: Context, db: DB):
    product = find_product(db, context, product_id)
    identity = listing_identity(product.source_url)
    if identity is None:
        raise HTTPException(422, "ใช้ URL หน้าสินค้า Shopee ที่มี Shop ID และ Item ID")
    url = affiliate_url(body)
    db.rollback()
    status = destination_status(url, identity, body.sub_id)
    if listing_identity(find_product(db, context, product_id, lock=True).source_url) != identity:
        raise HTTPException(409, "รายการสินค้าเปลี่ยนแล้ว กรุณาเลือกสินค้าอีกครั้ง")
    check_sub_id(db, context.workspace_id, channel, body.sub_id)
    return persist_channel_link(product_id, channel, body, context, db, shopee_verification=status)
