"""Live Reel publishing and read-back for the locally connected workspace."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, ForeignKeyConstraint, String, Text, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .auth import WorkspaceContext, require_workspace
from .config import Settings, get_settings
from .db import Base, get_db
from .meta_graph import MetaError, MetaGraph
from .products import ChannelLink, Product
from .publishing import MAX_VIDEO_BYTES
from .renders import Render, render_video_path

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/publishing/meta", tags=["publishing"])
Context = Annotated[WorkspaceContext, Depends(require_workspace)]
Database = Annotated[Session, Depends(get_db)]
Config = Annotated[Settings, Depends(get_settings)]
VideoId = Annotated[str, Field(pattern=r"^[0-9]{1,30}$")]


class MetaPublication(Base):
    __tablename__ = "meta_publications"
    __table_args__ = (ForeignKeyConstraint(
        ["workspace_id", "render_id"], ["renders.workspace_id", "renders.id"], ondelete="RESTRICT",
    ),)

    workspace_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    render_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    page_id: Mapped[str] = mapped_column(String(30))
    caption: Mapped[str] = mapped_column(Text)
    comment_message: Mapped[str | None] = mapped_column(Text)
    ai_generated: Mapped[bool] = mapped_column(Boolean)
    stage: Mapped[str] = mapped_column(String(32))
    video_id: Mapped[str | None] = mapped_column(String(30))
    comment_id: Mapped[str | None] = mapped_column(String(80))
    error: Mapped[str | None] = mapped_column(Text)


class PublishInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    render_id: str = Field(min_length=1, max_length=36)
    caption: str = Field(min_length=1, max_length=500)
    include_comment: bool = True
    ai_generated: bool = False


def available(context, settings):
    return bool(
        context.role == "owner" and context.workspace_id == settings.meta_studio_workspace_id
        and re.fullmatch(r"[0-9]{1,30}", settings.meta_test_page_id)
        and re.fullmatch(r"v[0-9]+\.[0-9]+", settings.meta_graph_api_version)
        and settings.meta_page_access_token.get_secret_value()
    )


def client(context, settings, *, write=False):
    if not available(context, settings):
        raise HTTPException(403, "Meta is not connected to this workspace owner")
    if write and not settings.meta_studio_publish_enabled:
        raise HTTPException(403, "Meta publishing is disabled for this Studio instance")
    return MetaGraph(settings)


def get_job(db, context, render_id):
    row = db.get(MetaPublication, (context.workspace_id, render_id))
    if row is None:
        raise HTTPException(404, "Meta publication not found")
    return row


def ensure_page(row, provider):
    if row.page_id != provider.page_id:
        raise HTTPException(409, "This render was already submitted to a different Facebook Page")


def advance(db, row, stages, target):
    result = db.execute(update(MetaPublication).where(
        MetaPublication.workspace_id == row.workspace_id,
        MetaPublication.render_id == row.render_id,
        MetaPublication.stage.in_(stages),
    ).values(stage=target))
    db.commit()
    return result.rowcount == 1


def job_data(row, live=None):
    return {
        "render_id": row.render_id, "stage": row.stage, "video_id": row.video_id,
        "include_comment": row.comment_message is not None, "comment_id": row.comment_id,
        "error": row.error, "reel": live,
        "can_post_comment": bool(row.comment_message and row.stage == "finish_requested"
                                 and live and live["publish_status"] == "published"),
    }


def comment_data(item, video_id):
    comment_id = str(item.get("id", ""))
    suffix = comment_id.rsplit("_", 1)[-1]
    return {
        "id": comment_id, "author": item["from"].get("name"),
        "message": item.get("message"), "hidden": item.get("is_hidden", False),
        "url": f"https://www.facebook.com/reel/{video_id}/?comment_id={suffix}"
        if re.fullmatch(r"[0-9]+", suffix) else None,
    }


def inspect(provider, video_id, job=None):
    video = provider.reel(video_id)
    status = video.get("status", {})
    publish_status = status.get("publishing_phase", {}).get("publish_status")
    verify_comment = job is not None and job.stage in {"comment_requested", "comment_sent"}
    recent = provider.comments(video_id, pages=5 if verify_comment else 1) if (
        publish_status == "published" and (job is None or verify_comment)
    ) else ()
    comments = [comment_data(item, video_id) for item in recent]
    matched = None
    if verify_comment and job.comment_message:
        for comment in comments:
            # New Page Experience can prefix the same comment ID with the post or video ID.
            same_id = (job.comment_id is None
                       or comment["id"].rsplit("_", 1)[-1] == job.comment_id.rsplit("_", 1)[-1])
            if same_id and not comment["hidden"] and comment["message"] == job.comment_message:
                matched = comment
                break
    return {
        "video_id": video_id, "page_name": video["from"].get("name"),
        "video_status": status.get("video_status"),
        "publish_status": publish_status,
        "url": f"https://www.facebook.com/reel/{video_id}/",
        "comments": comments if job is None else ([matched] if matched else []),
        "comment_verified": bool(matched),
    }


def read(provider, video_id, job=None):
    try:
        return inspect(provider, video_id, job)
    except MetaError as exc:
        raise HTTPException(502, str(exc)) from None


@router.get("")
def connection(context: Context, settings: Config):
    enabled = available(context, settings)
    return {
        "connected": enabled, "publish_enabled": enabled and settings.meta_studio_publish_enabled,
        "page_id": settings.meta_test_page_id if enabled else None,
        "page_name": settings.meta_studio_page_name if enabled else None,
        "example_reel_id": settings.meta_studio_example_reel_id if enabled else None,
    }


@router.get("/reels/{video_id}")
def read_existing(video_id: VideoId, context: Context, settings: Config):
    return read(client(context, settings), video_id)


@router.get("/publications/{render_id}")
def publication(render_id: str, context: Context, db: Database, settings: Config):
    provider = client(context, settings)
    row = db.get(MetaPublication, (context.workspace_id, render_id))
    if row is None:
        return None
    ensure_page(row, provider)
    live = read(provider, row.video_id, row) if row.video_id and row.stage in {
        "finish_requested", "comment_requested", "comment_sent",
    } else None
    return job_data(row, live)


@router.post("/publications", status_code=201)
def publish(payload: PublishInput, context: Context, db: Database, settings: Config):
    provider = client(context, settings, write=True)
    row = db.get(MetaPublication, (context.workspace_id, payload.render_id))
    if row:
        ensure_page(row, provider)
        return job_data(row)
    render = db.scalar(select(Render).where(
        Render.workspace_id == context.workspace_id, Render.id == payload.render_id,
    ))
    if render is None:
        raise HTTPException(404, "Render not found")
    product = db.get(Product, render.product_id)
    if render.status != "completed" or product is None or not product.image_rights_note:
        raise HTTPException(409, "Select a completed render and record its image rights")
    link = db.get(ChannelLink, (context.workspace_id, product.id, "facebook"))
    affiliate_url = link.affiliate_url if link else product.affiliate_url
    if payload.include_comment and not affiliate_url:
        raise HTTPException(422, "Add a Facebook affiliate URL before posting a comment")
    try:
        with render_video_path(render).open("rb") as video:
            content = video.read(MAX_VIDEO_BYTES + 1)
    except FileNotFoundError:
        raise HTTPException(404, "Render video not found") from None
    if not content or len(content) > MAX_VIDEO_BYTES:
        raise HTTPException(422, "The video is empty or exceeds 64 MiB")
    try:
        identity = provider.graph("me", params={"fields": "id"})
    except MetaError as exc:
        raise HTTPException(502, str(exc)) from None
    if str(identity.get("id")) != provider.page_id:
        raise HTTPException(409, "The Meta token belongs to a different Page")
    row = MetaPublication(
        workspace_id=context.workspace_id, render_id=render.id, page_id=provider.page_id,
        caption=payload.caption, ai_generated=payload.ai_generated, stage="starting",
        comment_message=(f"ดูรายละเอียดสินค้า {affiliate_url}\n\n"
                         "หากซื้อผ่านลิงก์นี้ เพจอาจได้รับค่าคอมมิชชัน") if payload.include_comment else None,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_job(db, context, payload.render_id)
        ensure_page(existing, provider)
        return job_data(existing)

    edge = f"{provider.page_id}/video_reels"
    try:
        started = provider.graph(edge, form={"upload_phase": "start"})
        video_id = str(started.get("video_id", ""))
        if not re.fullmatch(r"[0-9]{1,30}", video_id) or not isinstance(started.get("upload_url"), str):
            raise MetaError("Meta did not return a Reel upload session")
        row.video_id = video_id
        row.stage = "uploading"
        db.commit()
        provider.upload(started["upload_url"], video_id, content)
        row.stage = "finish_requested"
        db.commit()
        result = provider.graph(edge, form={
            "upload_phase": "finish", "video_id": video_id, "video_state": "PUBLISHED",
            "description": payload.caption, "is_ai_generated": str(payload.ai_generated).lower(),
        })
        if result.get("success") is not True:
            raise MetaError("Meta did not confirm the publish request")
    except MetaError as exc:
        row.error = str(exc)
        if row.stage != "finish_requested":
            row.stage = "upload_failed"
        db.commit()
    return job_data(row)


@router.post("/publications/{render_id}/comment")
def post_comment(render_id: str, context: Context, db: Database, settings: Config):
    provider = client(context, settings, write=True)
    row = get_job(db, context, render_id)
    ensure_page(row, provider)
    if not row.video_id or not row.comment_message or row.stage not in {
        "finish_requested", "comment_requested", "comment_sent",
    }:
        raise HTTPException(409, "This publication does not have a pending Affiliate comment")
    live = read(provider, row.video_id, row)
    if live["publish_status"] != "published":
        raise HTTPException(409, "The Reel is not published yet")
    if not advance(db, row, {"finish_requested"}, "comment_requested"):
        db.refresh(row)
        return job_data(row, live)
    try:
        result = provider.graph(f"{row.video_id}/comments", form={"message": row.comment_message})
        comment_id = str(result.get("id", ""))
        if not re.fullmatch(r"[0-9]+(?:_[0-9]+)?", comment_id):
            raise MetaError("Meta did not confirm the comment ID")
        row.comment_id = comment_id
        row.stage = "comment_sent"
        row.error = None
    except MetaError as exc:
        row.error = str(exc)
    db.commit()
    return job_data(row, read(provider, row.video_id, row))
