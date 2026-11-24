"""Campaign drafts and the durable publishing queue."""

from datetime import datetime, timezone
from time import time
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    select,
    update,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.content.renders import Render
from app.core.auth import WorkspaceContext, require_workspace
from app.core.config import Settings, get_settings
from app.core.db import Base, get_db
from app.publishing.meta_publishing import MetaPublication, PublishInput, available, publication

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/campaigns", tags=["campaigns"])
Context = Annotated[WorkspaceContext, Depends(require_workspace)]
Database = Annotated[Session, Depends(get_db)]
Config = Annotated[Settings, Depends(get_settings)]
MIN_LIVE_SPACING = 600


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (UniqueConstraint("workspace_id", "id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(12))
    page_id: Mapped[str | None] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(16), default="draft")
    created_at: Mapped[int] = mapped_column(BigInteger)


class CampaignItem(Base):
    __tablename__ = "campaign_items"
    __table_args__ = (
        ForeignKeyConstraint(["workspace_id", "campaign_id"], ["campaigns.workspace_id", "campaigns.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["workspace_id", "render_id"], ["renders.workspace_id", "renders.id"], ondelete="RESTRICT"),
        UniqueConstraint("campaign_id", "render_id"),
        Index("ix_campaign_due", "state", "next_run_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36))
    campaign_id: Mapped[str] = mapped_column(String(36))
    render_id: Mapped[str] = mapped_column(String(36))
    caption: Mapped[str] = mapped_column(Text)
    include_comment: Mapped[bool] = mapped_column(Boolean)
    ai_generated: Mapped[bool] = mapped_column(Boolean)
    scheduled_at: Mapped[int] = mapped_column(BigInteger)
    next_run_at: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(String(20), default="queued")
    checks: Mapped[int] = mapped_column(default=0)
    video_id: Mapped[str | None] = mapped_column(String(30))
    reel_url: Mapped[str | None] = mapped_column(Text)
    comment_url: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)


class CampaignWorkerState(Base):
    __tablename__ = "campaign_worker_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[int] = mapped_column(BigInteger)
    next_live_dispatch_at: Mapped[int] = mapped_column(BigInteger)
    heartbeat_at: Mapped[int | None] = mapped_column(BigInteger)


class ItemInput(PublishInput):
    scheduled_at: AwareDatetime


class CampaignInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    mode: Literal["simulation", "live"] = "simulation"
    items: list[ItemInput] = Field(min_length=1, max_length=500)


class Action(BaseModel):
    action: Literal["activate", "pause", "resume", "cancel"]


def iso_date(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def live_available(context: WorkspaceContext, settings: Settings) -> bool:
    return available(context, settings) and settings.meta_studio_publish_enabled and settings.campaign_live_enabled


def campaign_data(db, row):
    items = db.scalars(select(CampaignItem).where(
        CampaignItem.workspace_id == row.workspace_id, CampaignItem.campaign_id == row.id,
    ).order_by(CampaignItem.scheduled_at, CampaignItem.id)).all()
    return {
        "id": row.id, "name": row.name, "mode": row.mode, "state": row.state, "page_id": row.page_id,
        "items": [
            {"id": item.id, "render_id": item.render_id, "caption": item.caption,
             "scheduled_at": iso_date(item.scheduled_at), "state": item.state,
             "checks": item.checks, "video_id": item.video_id, "reel_url": item.reel_url,
             "comment_url": item.comment_url, "include_comment": item.include_comment, "error": item.error}
            for item in items
        ],
    }


def owner(context):
    if context.role != "owner":
        raise HTTPException(403, "Only the workspace owner can manage campaigns")


@router.get("")
def list_campaigns(context: Context, db: Database, settings: Config):
    rows = db.scalars(select(Campaign).where(Campaign.workspace_id == context.workspace_id)
                      .order_by(Campaign.created_at.desc(), Campaign.id).limit(50))
    return {"campaigns": [campaign_data(db, row) for row in rows],
            "live_enabled": live_available(context, settings), "page_name": settings.meta_studio_page_name}


@router.post("", status_code=201)
def create_campaign(payload: CampaignInput, context: Context, db: Database, settings: Config):
    owner(context)
    if payload.mode == "live" and not live_available(context, settings):
        raise HTTPException(403, "Live campaigns are disabled for this workspace")
    ids = {item.render_id for item in payload.items}
    if len(ids) != len(payload.items):
        raise HTTPException(422, "Each render can be used once per campaign")
    renders = set(db.scalars(select(Render.id).where(
        Render.workspace_id == context.workspace_id, Render.id.in_(ids), Render.status == "completed",
    )))
    if renders != ids:
        raise HTTPException(422, "Choose completed renders from this workspace")
    page_id = settings.meta_test_page_id if payload.mode == "live" else None
    if page_id:
        existing = db.scalar(select(MetaPublication.render_id).where(
            MetaPublication.workspace_id == context.workspace_id, MetaPublication.render_id.in_(ids),
        ).limit(1))
        if existing:
            raise HTTPException(409, "A selected render already has a live publication")
        slots = sorted(int(item.scheduled_at.timestamp()) for item in payload.items)
        if any(later - earlier < MIN_LIVE_SPACING for earlier, later in zip(slots, slots[1:])):
            raise HTTPException(422, "Live jobs in a campaign require at least 10 minutes between posts")
    row = Campaign(workspace_id=context.workspace_id, owner_id=context.user_id, name=payload.name,
                   mode=payload.mode, page_id=page_id, created_at=int(time()))
    db.add(row)
    db.flush()
    for item in payload.items:
        scheduled_at = int(item.scheduled_at.timestamp())
        db.add(CampaignItem(
            workspace_id=context.workspace_id, campaign_id=row.id, render_id=item.render_id,
            caption=item.caption, include_comment=item.include_comment, ai_generated=item.ai_generated,
            scheduled_at=scheduled_at, next_run_at=scheduled_at,
        ))
    db.commit()
    return campaign_data(db, row)


@router.post("/{campaign_id}/actions")
def campaign_action(campaign_id: str, body: Action, context: Context, db: Database, settings: Config):
    owner(context)
    row = db.scalar(select(Campaign).where(
        Campaign.workspace_id == context.workspace_id, Campaign.id == campaign_id,
    ))
    if row is None:
        raise HTTPException(404, "Campaign not found")
    allowed, target = {
        "activate": (("draft",), "active"),
        "pause": (("active",), "paused"),
        "resume": (("paused",), "active"),
        "cancel": (("draft", "active", "paused"), "cancelled"),
    }[body.action]
    if row.mode == "live" and target == "active" and (
        not live_available(context, settings) or row.page_id != settings.meta_test_page_id
    ):
        raise HTTPException(403, "The campaign's Facebook Page is unavailable")
    if row.mode == "live" and body.action == "activate" and db.scalar(select(CampaignItem.id).where(
        CampaignItem.campaign_id == row.id, CampaignItem.scheduled_at <= int(time()),
    ).limit(1)):
        raise HTTPException(409, "The campaign includes past times. Create a draft with future times.")
    result = db.execute(update(Campaign).where(
        Campaign.id == row.id, Campaign.state.in_(allowed),
    ).values(state=target, owner_id=context.user_id if target == "active" else row.owner_id))
    if not result.rowcount:
        raise HTTPException(409, "Action is unavailable in the current campaign state")
    if target == "cancelled":
        # Claimed work may already have reached the provider. Leave it visible for reconciliation.
        db.execute(update(CampaignItem).where(
            CampaignItem.campaign_id == row.id, CampaignItem.state == "queued",
        ).values(state="cancelled"))
    db.commit()
    return campaign_data(db, row)


@router.post("/{campaign_id}/items/{item_id}/reconcile")
def reconcile_item(campaign_id: str, item_id: str, context: Context, db: Database, settings: Config):
    owner(context)
    pair = db.execute(select(Campaign, CampaignItem).join(
        CampaignItem, CampaignItem.campaign_id == Campaign.id,
    ).where(Campaign.workspace_id == context.workspace_id, Campaign.id == campaign_id,
            CampaignItem.id == item_id)).first()
    if pair is None:
        raise HTTPException(404, "Campaign job not found")
    campaign, item = pair
    if campaign.mode != "live" or item.state != "needs_attention" or not item.video_id:
        raise HTTPException(409, "This job does not have a live publication awaiting review")
    result = publication(item.render_id, context, db, settings)
    live = result["reel"] if result else None
    if live and live["publish_status"] == "published":
        item.reel_url = live["url"]
        if not item.include_comment or live["comment_verified"]:
            item.comment_url = next((comment["url"] for comment in live["comments"]), None)
            item.state = "completed"
            item.error = None
        else:
            item.error = "The Reel is published, and Meta has not verified its Affiliate comment"
    db.commit()
    return campaign_data(db, campaign)
