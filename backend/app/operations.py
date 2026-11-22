"""Readiness and aggregate metrics for the private staging network."""

from pathlib import Path
from shutil import disk_usage
from time import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .campaigns import Campaign, CampaignItem, CampaignWorkerState
from .db import get_db
from .renders import render_root

router = APIRouter(prefix="/internal", include_in_schema=False)
BACKUP_RECEIPT = Path("/var/lib/studio/backups/last-success")


@router.get("/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(select(CampaignWorkerState.heartbeat_at).where(CampaignWorkerState.id == 1)).one()
    except SQLAlchemyError:
        raise HTTPException(503, "Database or campaign schema unavailable") from None
    return {"status": "ready"}


def backup_timestamp() -> int:
    try:
        return max(0, int(BACKUP_RECEIPT.read_text().strip()))
    except (OSError, ValueError):
        return 0


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(db: Session = Depends(get_db)):
    now = int(time())
    try:
        heartbeat = db.execute(select(CampaignWorkerState.heartbeat_at).where(
            CampaignWorkerState.id == 1,
        )).scalar_one()
        counts = db.execute(select(
            Campaign.mode, CampaignItem.state, func.count(),
        ).join(Campaign, Campaign.id == CampaignItem.campaign_id)
            .group_by(Campaign.mode, CampaignItem.state)).all()
        oldest = db.scalar(select(func.min(CampaignItem.next_run_at)).join(
            Campaign, Campaign.id == CampaignItem.campaign_id,
        ).where(
            Campaign.state == "active", Campaign.mode == "simulation",
            CampaignItem.state.in_(("queued", "dispatching", "verifying")),
            CampaignItem.next_run_at <= now,
        ))
    except SQLAlchemyError:
        raise HTTPException(503, "Database or campaign schema unavailable") from None

    root = render_root()
    free = disk_usage(root if root.exists() else root.parent if root.parent.exists() else Path.cwd()).free
    checked = (
        ("studio_worker_heartbeat_timestamp_seconds", heartbeat or 0),
        ("studio_campaign_oldest_due_seconds", now - oldest if oldest is not None else 0),
        ("studio_render_storage_free_bytes", free),
        ("studio_last_backup_timestamp_seconds", backup_timestamp()),
    )
    states = {(mode, state): count for mode, state, count in counts}
    lines = []
    for name, value in checked:
        lines.extend((f"# TYPE {name} gauge", f"{name} {value}"))
    lines.append("# TYPE studio_campaign_jobs gauge")
    for mode in ("simulation", "live"):
        for state in ("queued", "dispatching", "verifying", "completed", "needs_attention", "cancelled"):
            lines.append(f'studio_campaign_jobs{{mode="{mode}",state="{state}"}} {states.get((mode, state), 0)}')
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
