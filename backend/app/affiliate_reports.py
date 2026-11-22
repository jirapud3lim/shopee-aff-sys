"""Workspace-scoped Shopee CSV import and Affiliate report aggregation."""

import csv
from collections import defaultdict
from datetime import date, datetime, timezone
from itertools import groupby
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import BigInteger, Date, ForeignKey, Index, String, func, or_, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Mapped, Session, mapped_column
from starlette.concurrency import run_in_threadpool

from .auth import WorkspaceContext, require_workspace
from .db import Base, get_db
from .products import ChannelLink
from .shopee_report_csv import MONEY_SCALE, read_report

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/affiliate-reports", tags=["affiliate reports"])
Context = Annotated[WorkspaceContext, Depends(require_workspace)]
Database = Annotated[Session, Depends(get_db)]
ReportType = Literal["clicks", "orders"]
MAX_REPORT_BYTES = 25 * 1024 * 1024

class AffiliateReportRow(Base):
    __tablename__ = "affiliate_report_rows"
    __table_args__ = (Index("ix_affiliate_report_workspace_kind_day", "workspace_id", "kind", "day"),)

    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True,
    )
    kind: Mapped[str] = mapped_column(String(6), primary_key=True)
    row_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    day: Mapped[date] = mapped_column(Date)
    sub_id: Mapped[str | None] = mapped_column(String(600))
    source_channel: Mapped[str | None] = mapped_column(String(256))
    order_key: Mapped[str | None] = mapped_column(String(64))
    allocation: Mapped[str | None] = mapped_column(String(5))
    estimated: Mapped[int | None] = mapped_column(BigInteger)
    confirmed: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str | None] = mapped_column(String(10))
    updated: Mapped[str | None] = mapped_column(String(36))
    imported_at: Mapped[str] = mapped_column(String(36))


def save_report(db: Session, workspace_id: str, kind: ReportType, records: dict) -> int:
    insert = postgres_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    timestamp = datetime.now(timezone.utc).isoformat()
    if not records:
        return 0
    rows = [(key, records[key]) for key in sorted(records)]
    written = 0
    for offset in range(0, len(rows), 70):
        values = [
            dict.fromkeys(("order_key", "allocation", "estimated", "confirmed", "status", "updated"))
            | row | {"workspace_id": workspace_id, "kind": kind, "row_key": key, "imported_at": timestamp}
            for key, row in rows[offset:offset + 70]
        ]
        stmt = insert(AffiliateReportRow.__table__).values(values)
        excluded = stmt.excluded
        primary = ("workspace_id", "kind", "row_key")
        if kind == "clicks":
            stmt = stmt.on_conflict_do_nothing(index_elements=primary)
        else:
            changes = {
                key: excluded[key] for key in values[0]
                if key not in {*primary, "imported_at"}
            }
            changes["updated"] = func.coalesce(excluded.updated, AffiliateReportRow.updated)
            stmt = stmt.on_conflict_do_update(
                index_elements=primary,
                set_=changes | {"imported_at": excluded.imported_at},
                where=(
                    or_(AffiliateReportRow.updated.is_(None),
                        excluded.updated >= AffiliateReportRow.updated)
                    & or_(*(AffiliateReportRow.__table__.c[key].is_distinct_from(value)
                            for key, value in changes.items()))
                ),
            )
        result = db.execute(stmt)
        written += result.rowcount
    db.commit()
    return written


@router.post("/import/{kind}")
async def import_report(kind: ReportType, context: Context, db: Database, file: Annotated[UploadFile, File()]):
    try:
        content = await file.read(MAX_REPORT_BYTES + 1)
    finally:
        await file.close()
    if len(content) > MAX_REPORT_BYTES:
        raise HTTPException(413, "CSV exceeds 25 MiB")
    try:
        rows, duplicate_rows = await run_in_threadpool(read_report, content, kind)
    except (ValueError, csv.Error) as exc:
        raise HTTPException(422, str(exc)) from None
    written = await run_in_threadpool(save_report, db, context.workspace_id, kind, rows)
    return {"kind": kind, "rows": len(rows) + duplicate_rows, "saved": written,
            "skipped": len(rows) + duplicate_rows - written}


def attribution(sub_id, channel, links):
    matches = set()
    if sub_id:
        for token in sub_id.split("-"):
            matches.update(links.get(token.casefold(), ()))
    channels = {item[0] for item in matches}
    if channel not in channels and len(channels) == 1:
        channel = next(iter(channels))
    products = {product for matched_channel, product in matches if matched_channel == channel}
    return channel or "unknown", sub_id, next(iter(products)) if len(products) == 1 else None


def order_totals(rows):
    eligible = [row for row in rows if row.status not in {"cancelled", "unpaid"}]
    order_amounts = [row for row in rows if row.allocation == "order"]
    if order_amounts:
        latest = max(order_amounts, key=lambda row: (row.imported_at, row.updated or "", row.row_key))
        estimated = latest.estimated or 0 if eligible else 0
    else:
        estimated = sum(row.estimated or 0 for row in eligible)
    # A completed order is not necessarily paid out. Prefer an explicit confirmed amount.
    confirmed_rows = [row for row in eligible if row.confirmed is not None]
    if order_amounts:
        explicit = [row for row in confirmed_rows if row.allocation == "order"]
        if explicit:
            confirmed = max(explicit, key=lambda row: (row.imported_at, row.row_key)).confirmed
        else:
            confirmed = estimated if eligible and all(row.status == "completed" for row in eligible) else 0
    else:
        confirmed = sum(row.confirmed if row.confirmed is not None else
                        (row.estimated or 0 if row.status == "completed" else 0) for row in eligible)
    return estimated, confirmed


@router.get("")
def summary(context: Context, db: Database, start: date | None = None, end: date | None = None):
    workspace = context.workspace_id
    if start and end and start > end:
        raise HTTPException(422, "Report start must be on or before the end date")
    links = defaultdict(set)
    for channel, sub_id, product_id in db.execute(select(
        ChannelLink.channel, ChannelLink.sub_id, ChannelLink.product_id,
    ).where(ChannelLink.workspace_id == workspace, ChannelLink.sub_id.is_not(None))):
        links[sub_id.casefold()].add((channel, product_id))
    base = db.query(AffiliateReportRow).filter(AffiliateReportRow.workspace_id == workspace)
    bounds = {
        kind: {"first": first, "last": last}
        for kind, first, last in base.with_entities(
            AffiliateReportRow.kind, func.min(AffiliateReportRow.day), func.max(AffiliateReportRow.day),
        ).group_by(AffiliateReportRow.kind)
    }
    if end is None and bounds:
        end = max(source["last"] for source in bounds.values())
    if start is None and end:
        start = date.fromordinal(max(1, end.toordinal() - 59))
    filters = []
    if start:
        filters.append(AffiliateReportRow.day >= start)
    if end:
        filters.append(AffiliateReportRow.day <= end)

    totals = defaultdict(lambda: [0, 0, 0, 0])
    grouped_clicks = base.filter(*filters, AffiliateReportRow.kind == "clicks").with_entities(
        AffiliateReportRow.day, AffiliateReportRow.sub_id, AffiliateReportRow.source_channel,
        func.count(),
    ).group_by(AffiliateReportRow.day, AffiliateReportRow.sub_id, AffiliateReportRow.source_channel)
    for day, sub_id, source_channel, count in grouped_clicks:
        totals[(day, *attribution(sub_id, source_channel, links))][0] += count

    orders = base.filter(*filters, AffiliateReportRow.kind == "orders").order_by(
        AffiliateReportRow.order_key, AffiliateReportRow.row_key,
    ).yield_per(1000)
    for _, group in groupby(orders, key=lambda row: row.order_key):
        rows = list(group)
        tags = {(row.sub_id, row.source_channel) for row in rows}
        sub_ids = {sub_id for sub_id, _ in tags if sub_id}
        sub_id = next(iter(sub_ids)) if len(sub_ids) == 1 else None
        channels = {channel for _, channel in tags if channel}
        channel_hint = next(iter(channels)) if len(channels) == 1 else None
        bucket = totals[(min(row.day for row in rows), *attribution(sub_id, channel_hint, links))]
        estimated, confirmed = order_totals(rows)
        bucket[1] += 1
        bucket[2] += estimated
        bucket[3] += confirmed
    return {
        "sources": bounds,
        "days": [
            {"date": day, "channel": channel, "sub_id": sub_id, "product_id": product_id,
             "clicks": clicks, "orders": orders, "estimated": estimated / MONEY_SCALE,
             "confirmed": confirmed / MONEY_SCALE}
            for (day, channel, sub_id, product_id), (clicks, orders, estimated, confirmed)
            in sorted(totals.items(), key=lambda item: (
                item[0][0], item[0][1], item[0][2] or "", item[0][3] or "",
            ))
        ],
    }
