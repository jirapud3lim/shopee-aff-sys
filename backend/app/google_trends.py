"""Thailand Trending Now results and explainable workspace product matches."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from math import log1p
import re
from threading import Lock
from typing import Annotated, Literal
from unicodedata import normalize
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .affiliate_reports import product_activity
from .auth import WorkspaceContext, require_workspace
from .db import get_db
from .products import Product
from .shopee_report_csv import BANGKOK
from .shopee_offers import ShopeeOffer

FEED_URL = "https://trends.google.com/trending/rss?geo=TH"
SOURCE_URL = "https://trends.google.com/trending?geo=TH"
MAX_FEED_BYTES = 512 * 1024
FEED_TTL = timedelta(minutes=10)
RETRY_DELAY = timedelta(minutes=1)
STALE_LIMIT = timedelta(hours=24)
HISTORY_DAYS = 30
SCORE_WEIGHTS = {"trend": 25, "relevance": 35, "clicks": 15, "orders": 25}
STOP_WORDS = frozenset((
    "สำหรับ", "ของ", "ใน", "ขนาด", "แบบ", "แพ็ก", "แพ็ค", "ตัว", "สินค้า", "ใหม่",
    "ราคา", "รีวิว", "วันนี้", "ไทย", "ออนไลน์", "ดีที่สุด", "ที่", "และ", "มี", "คือ",
    "best", "with", "for", "shop", "buy", "new", "sale", "online", "review", "the",
))
router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/trends", tags=["trends"])
Context = Annotated[WorkspaceContext, Depends(require_workspace)]
Database = Annotated[Session, Depends(get_db)]


class FeedError(Exception):
    pass


@dataclass(frozen=True)
class Trend:
    title: str
    published_at: datetime | None
    traffic: str | None


@dataclass(frozen=True)
class Snapshot:
    entries: tuple[Trend, ...]
    fetched_at: datetime


def parse_feed(payload: bytes) -> tuple[Trend, ...]:
    raw = payload.decode("utf-8-sig")
    if "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        raise FeedError("Unexpected RSS declaration")
    root = ET.fromstring(raw)
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise FeedError("Unexpected Google Trends feed format")

    entries = []
    seen = set()
    for item in channel.findall("item")[:100]:
        fields = {element.tag.rsplit("}", 1)[-1]: (element.text or "").strip() for element in item}
        title = " ".join(fields.get("title", "").split())[:180]
        key = normalize("NFC", title).casefold()
        if not title or key in seen:
            continue
        seen.add(key)
        try:
            published = parsedate_to_datetime(fields.get("pubDate", ""))
            published = published.astimezone(timezone.utc) if published.tzinfo else None
        except (ValueError, TypeError, OverflowError):
            published = None
        entries.append(Trend(title, published, fields.get("approx_traffic", "")[:24] or None))
    return tuple(entries)


def fetch_feed() -> tuple[Trend, ...]:
    request = Request(FEED_URL, headers={"Accept": "application/rss+xml, text/xml",
                                        "User-Agent": "AffiliateStudio/1.0 Google-Trends-RSS"})
    with urlopen(request, timeout=6) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise FeedError("Google Trends RSS exceeded the response size limit")
    return parse_feed(payload)


class FeedCache:
    def __init__(self):
        self.lock = Lock()
        self.snapshot: Snapshot | None = None
        self.retry_at: datetime | None = None

    def get(self, now: datetime) -> tuple[Snapshot, bool]:
        with self.lock:
            snapshot = self.snapshot
            if snapshot and now - snapshot.fetched_at < FEED_TTL:
                return snapshot, False
            if not self.retry_at or now >= self.retry_at:
                try:
                    snapshot = Snapshot(fetch_feed(), now)
                except (OSError, ValueError, ET.ParseError, FeedError):
                    self.retry_at = now + RETRY_DELAY
                else:
                    self.snapshot = snapshot
                    self.retry_at = None
                    return snapshot, False
            if snapshot and now - snapshot.fetched_at <= STALE_LIMIT:
                return snapshot, True
            raise FeedError("Google Trends is temporarily unavailable")


cache = FeedCache()


def tokens(text: str) -> tuple[str, ...]:
    from pythainlp.tokenize import word_tokenize

    # Preserve Thai sara am for dictionary lookup after normalizing full-width Latin text.
    canonical = normalize("NFKC", text).replace("\u0e4d\u0e32", "\u0e33").casefold()
    canonical = "".join(
        char if char.isalnum() or "\u0e31" <= char <= "\u0e4e" else " " for char in canonical
    )
    return tuple(part for part in word_tokenize(canonical, engine="newmm-safe", keep_whitespace=False)
                 if len(part) >= 3 and any(letter.isalpha() for letter in part)
                 and part not in STOP_WORDS)


def is_shopee(source_url: str) -> bool:
    host = urlsplit(source_url).hostname or ""
    return host == "shopee.co.th" or host.endswith(".shopee.co.th")


def catalog(db: Session, workspace_id: str):
    rows = db.execute(select(Product.id, Product.name, Product.source_url)
                      .where(Product.workspace_id == workspace_id)).all()
    return [(row.id, row.name, tokens(row.name)) for row in rows if is_shopee(row.source_url)]


def match(title: str, products):
    query = tokens(title)
    distinct = tuple(dict.fromkeys(query))
    if not distinct:
        return []
    matches = []
    for product_id, name, words in products:
        word_set = set(words)
        shared = [word for word in distinct if word in word_set]
        coverage = len(shared) / len(distinct)
        if len(distinct) == 1:
            if not shared or len(distinct[0]) < 5:
                continue
        elif len(shared) < 2 or coverage < 0.6:
            continue
        phrase = len(query) > 1 and any(
            words[index:index + len(query)] == query for index in range(len(words) - len(query) + 1)
        )
        matches.append({
            "product_id": product_id, "name": name, "terms": shared, "phrase": phrase,
            "coverage": round(100 * coverage),
        })
    matches.sort(key=lambda item: (
        -item["coverage"], not item["phrase"], -len(item["terms"]), item["name"], item["product_id"],
    ))
    return matches


def traffic_count(value: str | None) -> int | None:
    found = re.fullmatch(r"(\d+(?:\.\d+)?)([KM])?\+?", (value or "").replace(",", "").upper())
    if found is None:
        return None
    multiplier = {None: 1, "K": 1000, "M": 1000000}[found[2]]
    return int(float(found[1]) * multiplier)


def volume_points(value: int | None, cap: int, weight: int) -> int:
    return round(weight * log1p(min(value or 0, cap)) / log1p(cap))


def opportunity(item, searches, clicks, orders):
    points = {
        "trend": volume_points(searches, 100_000, SCORE_WEIGHTS["trend"]),
        "relevance": round(30 * item["coverage"] / 100) + 5 * item["phrase"],
        "clicks": volume_points(clicks, 100, SCORE_WEIGHTS["clicks"]),
        "orders": volume_points(orders, 20, SCORE_WEIGHTS["orders"]),
    }
    return {"total": sum(points.values()), "points": points, "clicks": clicks, "orders": orders,
            "searches": searches}


def explore_url(title: str) -> str:
    return "https://trends.google.com/trends/explore?" + urlencode({"geo": "TH", "q": title})


@router.get("")
def list_trends(
    context: Context, db: Database, hours: Literal["4", "24"] = "24",
    include_offers: bool = False,
):
    now = datetime.now(timezone.utc)
    try:
        snapshot, stale = cache.get(now)
    except FeedError as exc:
        raise HTTPException(503, str(exc)) from None
    products = catalog(db, context.workspace_id)
    offers = []
    if include_offers:
        rows = db.execute(
            select(ShopeeOffer.offer_id, ShopeeOffer.name)
            .where(ShopeeOffer.workspace_id == str(context.workspace_id))
        )
        offers = [(row.offer_id, row.name, tokens(row.name)) for row in rows]
    entries = []
    for trend in snapshot.entries:
        if trend.published_at and trend.published_at < now - timedelta(hours=int(hours)):
            continue
        if not trend.published_at and hours == "4":
            continue
        entries.append({
            "title": trend.title, "published_at": trend.published_at, "traffic": trend.traffic,
            "explore_url": explore_url(trend.title), "matches": match(trend.title, products),
        })
        if include_offers:
            entries[-1]["offer_matches"] = [
                {"offer_id": item["product_id"], "score": opportunity(
                    item, traffic_count(trend.traffic), None, None,
                )["total"]}
                for item in match(trend.title, offers)[:5]
            ]
    end = now.astimezone(BANGKOK).date()
    start = end - timedelta(days=HISTORY_DAYS - 1)
    candidates = {item["product_id"] for entry in entries for item in entry["matches"]}
    clicks, orders = product_activity(db, context.workspace_id, start, end, candidates)
    for entry in entries:
        searches = traffic_count(entry["traffic"])
        for item in entry["matches"]:
            product_id = item["product_id"]
            item["opportunity"] = opportunity(item, searches, clicks.get(product_id), orders.get(product_id))
        entry["matches"].sort(key=lambda item: -item["opportunity"]["total"])
        entry["matches"] = entry["matches"][:5]
    return {"region": "TH", "source_url": SOURCE_URL, "fetched_at": snapshot.fetched_at,
            "stale": stale, "catalog_count": len(products), "trends": entries,
            "scoring": {"weights": SCORE_WEIGHTS, "start": start, "end": end}}


@router.get("/matches")
def lookup_products(context: Context, db: Database, q: Annotated[str, Query(min_length=2, max_length=180)]):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(422, "Enter a search phrase")
    products = catalog(db, context.workspace_id)
    return {"query": query, "explore_url": explore_url(query),
            "matches": match(query, products)[:5], "catalog_count": len(products)}
