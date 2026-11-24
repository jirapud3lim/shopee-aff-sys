"""Persistent publishing simulations using the same orchestration as the feasibility spike."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from publish_spike.domain import Phase, VideoPublishStatus, make_idempotency_key
from publish_spike.fake_meta import Behavior, FakeMetaReels
from publish_spike.service import PublishService
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, Boolean, ForeignKeyConstraint, String, Text, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.catalog.products import ChannelLink, Product
from app.content.renders import Render, render_video_path
from app.core.auth import WorkspaceContext, require_workspace
from app.core.db import Base, get_db

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/publishing/simulations", tags=["publishing"]
)
SIMULATED_PAGE = "local-test-page"
MAX_VIDEO_BYTES = 64 * 1024 * 1024


class PublishingSimulation(Base):
    __tablename__ = "publishing_simulations"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "render_id", name="uq_publishing_simulation_workspace_render"
        ),
        ForeignKeyConstraint(
            ["workspace_id", "render_id"],
            ["renders.workspace_id", "renders.id"],
            ondelete="CASCADE",
            name="fk_simulation_workspace_render",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36))
    render_id: Mapped[str] = mapped_column(String(36))
    caption: Mapped[str] = mapped_column(Text)
    include_comment: Mapped[bool] = mapped_column(Boolean)
    video_status: Mapped[str] = mapped_column(String(32))
    comment_status: Mapped[str] = mapped_column(String(32))
    comment_verified: Mapped[bool] = mapped_column(Boolean)
    attempts: Mapped[list[dict[str, str]]] = mapped_column(JSON)


class SimulationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    render_id: str = Field(min_length=1, max_length=36)
    caption: str = Field(min_length=1, max_length=500)
    include_comment: bool = False


class SimulationOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    render_id: str
    caption: str
    include_comment: bool
    video_status: str
    comment_status: str
    comment_verified: bool
    attempts: list[dict[str, str]]
    provider: str = "simulated"


def existing_simulation(db: Session, workspace_id: str, payload: SimulationInput):
    simulation = db.scalar(
        select(PublishingSimulation).where(
            PublishingSimulation.workspace_id == workspace_id,
            PublishingSimulation.render_id == payload.render_id,
        )
    )
    if simulation and (simulation.caption, simulation.include_comment) != (
        payload.caption,
        payload.include_comment,
    ):
        raise HTTPException(
            409,
            "This video already has a simulation with different settings. Render a new version first.",
        )
    return simulation


@router.get("", response_model=list[SimulationOutput])
def list_simulations(
    context: WorkspaceContext = Depends(require_workspace), db: Session = Depends(get_db)
):
    return db.scalars(
        select(PublishingSimulation)
        .where(PublishingSimulation.workspace_id == context.workspace_id)
        .order_by(PublishingSimulation.id)
        .limit(100)
    ).all()


@router.post("", response_model=SimulationOutput, status_code=201)
def simulate(
    payload: SimulationInput,
    response: Response,
    context: WorkspaceContext = Depends(require_workspace),
    db: Session = Depends(get_db),
):
    existing = existing_simulation(db, context.workspace_id, payload)
    if existing:
        response.status_code = 200
        return existing

    render = db.scalar(
        select(Render).where(
            Render.id == payload.render_id, Render.workspace_id == context.workspace_id
        )
    )
    if render is None:
        raise HTTPException(404, "Render not found")
    if render.status != "completed":
        raise HTTPException(409, "Only completed videos can be simulated")
    product = db.scalar(
        select(Product).where(
            Product.id == render.product_id, Product.workspace_id == context.workspace_id
        )
    )
    if product is None or not product.image_rights_note:
        raise HTTPException(409, "Record the product image rights before running a simulation")
    facebook_link = db.get(ChannelLink, (context.workspace_id, product.id, "facebook"))
    affiliate_url = facebook_link.affiliate_url if facebook_link else product.affiliate_url
    if payload.include_comment and not affiliate_url:
        raise HTTPException(422, "Add an affiliate URL to simulate a comment")

    try:
        with render_video_path(render).open("rb") as video:
            video_bytes = video.read(MAX_VIDEO_BYTES + 1)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Render video not found") from exc
    if not video_bytes or len(video_bytes) > MAX_VIDEO_BYTES:
        raise HTTPException(422, "The video is empty or exceeds the simulation size limit")

    def now() -> datetime:
        return datetime.now(timezone.utc)

    provider = FakeMetaReels(now)
    provider.script(Phase.FINISH, Behavior.TIMEOUT_APPLIED)
    service = PublishService(provider, now)
    key = make_idempotency_key(context.workspace_id, render.product_id, SIMULATED_PAGE, render.id)
    job = service.run(
        service.submit(key, SIMULATED_PAGE, payload.caption, affiliate_url or ""),
        video_bytes,
    )
    if job.status is VideoPublishStatus.UNKNOWN:
        service.reconcile(job)
    verified = False
    if (
        payload.include_comment
        and job.status is VideoPublishStatus.PUBLISHED
        and job.remote_video_id
    ):
        service.request_comment(job)
        service.post_comment(job)
        verified = any(
            comment.comment_id == job.comment_id
            and comment.author_id == SIMULATED_PAGE
            and comment.message == affiliate_url
            for comment in provider.list_comments(job.remote_video_id)
        )

    simulation = PublishingSimulation(
        workspace_id=context.workspace_id,
        render_id=render.id,
        caption=payload.caption,
        include_comment=payload.include_comment,
        video_status=job.status.value,
        comment_status=job.comment_status.value,
        comment_verified=verified,
        attempts=[
            {"phase": attempt.phase.value, "outcome": attempt.outcome} for attempt in job.attempts
        ],
    )
    db.add(simulation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = existing_simulation(db, context.workspace_id, payload)
        if existing is None:
            raise
        response.status_code = 200
        return existing
    db.refresh(simulation)
    return simulation
