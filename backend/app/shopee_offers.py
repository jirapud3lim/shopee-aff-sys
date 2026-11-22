"""Workspace snapshots of offers visible in the Shopee Affiliate portal."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from .auth import require_workspace
from .db import Base, get_db

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/shopee-offers", tags=["shopee-offers"])
OfferId = Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{0,19}$")]


class ShopeeOffer(Base):
    __tablename__ = "shopee_offers"

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    offer_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    sold: Mapped[int] = mapped_column(Integer)
    sold_is_minimum: Mapped[bool]
    price_satang: Mapped[int] = mapped_column(BigInteger)
    commission_bps: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OfferInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    offer_id: OfferId
    name: str = Field(min_length=1, max_length=300)
    sold: int = Field(ge=0, le=2_147_483_647, strict=True)
    sold_is_minimum: bool
    price_satang: int = Field(gt=0, le=9_999_999_999, strict=True)
    commission_bps: int = Field(ge=0, le=10_000, strict=True)


class OfferSnapshot(OfferInput):
    model_config = ConfigDict(from_attributes=True)
    observed_at: datetime


class OfferBatch(BaseModel):
    offers: list[OfferInput] = Field(min_length=1, max_length=100)


@router.get("", response_model=list[OfferSnapshot])
def list_offers(
    context: Any = Depends(require_workspace),
    db: Session = Depends(get_db),
):
    snapshots = db.scalars(
        select(ShopeeOffer).where(ShopeeOffer.workspace_id == str(context.workspace_id))
        .order_by(ShopeeOffer.observed_at.desc(), ShopeeOffer.offer_id)
    )
    return [
        OfferSnapshot.model_validate(offer).model_copy(
            update={"observed_at": offer.observed_at.replace(tzinfo=UTC)}
        )
        for offer in snapshots
    ]


@router.post("")
def capture_offers(
    batch: OfferBatch,
    context: Any = Depends(require_workspace),
    db: Session = Depends(get_db),
):
    workspace = str(context.workspace_id)
    observed_at = datetime.now(UTC)
    unique = {offer.offer_id: offer.model_dump() for offer in batch.offers}
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else postgres_insert
    # A stable lock order also covers overlapping batches.
    rows = [
        dict(unique[offer_id], workspace_id=workspace, observed_at=observed_at)
        for offer_id in sorted(unique)
    ]
    statement = insert(ShopeeOffer).values(rows)
    db.execute(statement.on_conflict_do_update(
        index_elements=[ShopeeOffer.workspace_id, ShopeeOffer.offer_id],
        set_={key: statement.excluded[key] for key in rows[0] if key not in ("workspace_id", "offer_id")},
        where=ShopeeOffer.observed_at <= statement.excluded.observed_at,
    ))
    db.commit()
    return {"saved": len(rows)}
