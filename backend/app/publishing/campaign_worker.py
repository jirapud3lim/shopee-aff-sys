"""Poll the campaign queue from a separate worker process."""

import argparse
import logging
import random
from time import sleep, time
from uuid import uuid4

from fastapi import HTTPException, Response
from sqlalchemy import and_, or_, select, update

from app.core.auth import WorkspaceContext
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.models import OrganizationMember, User
from app.publishing.campaigns import (
    MIN_LIVE_SPACING,
    Campaign,
    CampaignItem,
    CampaignWorkerState,
    live_available,
)
from app.publishing.meta_publishing import (
    MetaPublication,
    PublishInput,
    post_comment,
    publication,
    publish,
)
from app.publishing.publishing import SimulationInput, simulate

logger = logging.getLogger(__name__)
LEASE_SECONDS = 900
MAX_CHECKS = 10


def acquire(db, token, now):
    result = db.execute(update(CampaignWorkerState).where(
        CampaignWorkerState.id == 1, CampaignWorkerState.lease_until <= now,
    ).values(lease_token=token, lease_until=now + LEASE_SECONDS))
    db.commit()
    return result.rowcount == 1


def release(db, token):
    db.rollback()
    db.execute(update(CampaignWorkerState).where(
        CampaignWorkerState.id == 1, CampaignWorkerState.lease_token == token,
    ).values(lease_token=None, lease_until=0))
    db.commit()


def heartbeat(db, now):
    db.execute(update(CampaignWorkerState).where(
        CampaignWorkerState.id == 1,
        or_(CampaignWorkerState.heartbeat_at.is_(None), CampaignWorkerState.heartbeat_at <= now - 5),
    ).values(heartbeat_at=now))
    db.commit()


def claim(db, now, live_enabled):
    worker = db.get(CampaignWorkerState, 1)
    row = db.execute(select(CampaignItem, Campaign).join(
        Campaign, Campaign.id == CampaignItem.campaign_id,
    ).where(
        or_(Campaign.mode == "simulation", live_enabled),
        CampaignItem.next_run_at <= now,
        or_(
            and_(
                Campaign.state == "active", CampaignItem.state == "queued",
                or_(Campaign.mode == "simulation", worker.next_live_dispatch_at <= now),
            ),
            and_(Campaign.state.in_(("active", "paused", "cancelled")),
                 CampaignItem.state.in_(("dispatching", "verifying"))),
        ),
    ).order_by(CampaignItem.next_run_at, CampaignItem.id).limit(1)).first()
    if row is None:
        return None
    item, campaign = row
    if item.state == "queued":
        eligible = select(Campaign.id).where(Campaign.id == campaign.id, Campaign.state == "active")
        result = db.execute(update(CampaignItem).where(
            CampaignItem.id == item.id, CampaignItem.state == "queued",
            CampaignItem.campaign_id.in_(eligible),
        ).values(state="dispatching"))
        if not result.rowcount:
            db.rollback()
            return None
    db.commit()
    return item, campaign


def defer(item, now, error=None):
    item.checks += 1
    if item.checks >= MAX_CHECKS:
        item.state = "needs_attention"
        item.error = error or "Provider status is still unresolved"
    else:
        item.state = "verifying"
        delay = min(180, 5 * 2 ** (item.checks - 1))
        item.next_run_at = now + delay + random.randint(0, 5)
        item.error = error


def member_context(db, campaign):
    member = db.scalar(select(OrganizationMember).join(User).where(
        OrganizationMember.organization_id == campaign.workspace_id,
        OrganizationMember.user_id == campaign.owner_id, User.is_active.is_(True),
    ))
    if not member or member.role != "owner":
        raise HTTPException(403, "The campaign owner no longer has access")
    return WorkspaceContext(campaign.workspace_id, campaign.owner_id, member.role)


def process(db, item, campaign, settings, now):
    context = member_context(db, campaign)
    db.refresh(campaign)
    if campaign.mode == "simulation":
        if campaign.state != "active":
            item.state = "cancelled" if campaign.state == "cancelled" else "queued"
            return
        result = simulate(SimulationInput(
            render_id=item.render_id, caption=item.caption, include_comment=item.include_comment,
        ), Response(), context, db)
        item.state = "completed" if result.video_status == "published" and (
            not item.include_comment or result.comment_verified
        ) else "needs_attention"
        return

    if not live_available(context, settings) or campaign.page_id != settings.meta_test_page_id:
        raise HTTPException(403, "Live campaign access is unavailable")
    remote = db.get(MetaPublication, (item.workspace_id, item.render_id))
    if remote is None and item.state == "dispatching":
        if campaign.state != "active":
            item.state = "cancelled" if campaign.state == "cancelled" else "queued"
            return
        worker = db.get(CampaignWorkerState, 1)
        if worker.next_live_dispatch_at > now:
            item.next_run_at = worker.next_live_dispatch_at
            return
        worker.next_live_dispatch_at = now + MIN_LIVE_SPACING
        db.commit()
        result = publish(PublishInput(
            render_id=item.render_id, caption=item.caption, include_comment=item.include_comment,
            ai_generated=item.ai_generated,
        ), context, db, settings)
    elif remote:
        if (remote.caption, bool(remote.comment_message), remote.ai_generated) != (
            item.caption, item.include_comment, item.ai_generated,
        ):
            raise HTTPException(409, "This render has a publication with different settings")
        result = publication(item.render_id, context, db, settings)
    else:
        raise HTTPException(409, "The saved publication could not be found")

    item.video_id = result["video_id"]
    if result["stage"] in {"starting", "uploading", "upload_failed"}:
        item.state = "needs_attention"
        item.error = result["error"] or "Upload did not reach publishing. Check the saved publication."
        return

    live = result["reel"]
    if live and live["video_status"] == "error":
        item.state = "needs_attention"
        item.error = result["error"] or "Meta reported a video processing or publication error"
        return
    if not live or live["publish_status"] != "published":
        defer(item, now, result["error"])
        return
    item.reel_url = live["url"]
    db.refresh(campaign)
    if result["can_post_comment"] and campaign.state == "active":
        result = post_comment(item.render_id, context, db, settings)
        live = result["reel"]
    if item.include_comment and not live["comment_verified"]:
        if result["can_post_comment"] and campaign.state != "active":
            item.state = "verifying" if campaign.state == "paused" else "cancelled"
            item.next_run_at = now + 30
        else:
            defer(item, now, result["error"])
        return
    item.comment_url = next((comment["url"] for comment in live["comments"]), None)
    item.state = "completed"
    item.error = None


def tick(db, settings, now=None):
    now = int(time()) if now is None else now
    token = str(uuid4())
    if not acquire(db, token, now):
        return False
    try:
        claimed = claim(db, now, settings.campaign_live_enabled)
        if claimed is None:
            return False
        item, campaign = claimed
        try:
            process(db, item, campaign, settings, now)
        except HTTPException as exc:
            if exc.status_code == 502 and campaign.mode == "live":
                remote = db.get(MetaPublication, (item.workspace_id, item.render_id))
                if remote:
                    item.video_id = remote.video_id
                    defer(item, now, str(exc.detail))
                else:
                    item.checks += 1
                    item.state = "needs_attention" if item.checks >= MAX_CHECKS else "dispatching"
                    item.next_run_at = now + MIN_LIVE_SPACING
                    item.error = str(exc.detail)
            else:
                item.state = "needs_attention"
                item.error = str(exc.detail)
        db.commit()
        logger.info("campaign=%s job=%s status=%s", campaign.id, item.id, item.state)
        return True
    finally:
        release(db, token)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process at most one due job")
    options = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    while True:
        try:
            with SessionLocal() as db:
                worked = tick(db, settings)
                heartbeat(db, int(time()))
        except Exception:
            logger.exception("Campaign worker iteration failed")
            if options.once:
                raise
            worked = False
        if options.once:
            break
        if not worked:
            sleep(5)


if __name__ == "__main__":
    main()
