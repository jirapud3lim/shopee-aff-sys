from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import google_trends
from app.auth import WorkspaceContext, require_workspace
from app.db import Base, get_db
from app.models import Organization
from app.products import Product


def test_feed_age_and_thai_matches_are_workspace_scoped(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as db:
        db.add_all([Organization(id="a", name="A"), Organization(id="b", name="B")])
        db.flush()
        db.add_all([
            Product(id="cloth-a", workspace_id="a", name="ผ้าไมโครไฟเบอร์สำหรับงานครัว Scotch-Brite",
                    source_url="https://shopee.co.th/product/1/2"),
            Product(id="cloth-b", workspace_id="b", name="ผ้าไมโครไฟเบอร์ ผืนใหญ่",
                    source_url="https://shopee.co.th/product/1/3"),
            Product(id="other", workspace_id="a", name="ผ้าไมโครไฟเบอร์",
                    source_url="https://shopee.co.th.example.com/product/1/2"),
        ])

    def session():
        with sessions() as db:
            yield db

    now = datetime.now(timezone.utc)
    recent = format_datetime(now - timedelta(hours=1))
    yesterday = format_datetime(now - timedelta(hours=12))
    payload = f"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:ht="https://trends.google.com/trending/rss">
          <channel>
            <item><title>ผ้าไมโครไฟเบอร์</title>
              <ht:approx_traffic>200+</ht:approx_traffic><pubDate>{recent}</pubDate>
              <link>https://example.com/untrusted-link</link>
            </item>
            <item><title>ฟุตบอล</title><pubDate>{yesterday}</pubDate></item>
            <item><title>ผ้าไมโครไฟเบอร์</title><pubDate>{recent}</pubDate></item>
          </channel>
        </rss>""".encode()
    calls = []

    def fetch():
        calls.append(1)
        return google_trends.parse_feed(payload)

    monkeypatch.setattr(google_trends, "fetch_feed", fetch)
    monkeypatch.setattr(google_trends, "cache", google_trends.FeedCache())
    app = FastAPI()
    app.include_router(google_trends.router)
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[require_workspace] = lambda workspace_id: WorkspaceContext(
        workspace_id, "user", "owner",
    )
    with TestClient(app) as client:
        path = "/api/v1/workspaces/a/trends"
        four_hours = client.get(path, params={"hours": "4"}).raise_for_status().json()
        assert four_hours["catalog_count"] == 1
        trend, = four_hours["trends"]
        assert trend["traffic"] == "200+"
        result, = trend["matches"]
        assert result["product_id"] == "cloth-a"
        assert result["terms"] and result["phrase"]
        assert trend["explore_url"].startswith("https://trends.google.com/")
        assert len(client.get(path).json()["trends"]) == 2
        assert client.get(path).json()["trends"][1]["matches"] == []
        assert client.get(path, params={"hours": "72"}).status_code == 422
        matched_b = client.get(path.replace("/a/", "/b/") + "/matches", params={"q": "ผ้าไมโครไฟเบอร์"})
        assert [result["product_id"] for result in matched_b.json()["matches"]] == ["cloth-b"]
        assert client.get(path + "/matches", params={"q": "Scotch-Brite"}).json()["matches"][0]["product_id"] == "cloth-a"
        assert client.get(path + "/matches", params={"q": "ผ้า"}).json()["matches"] == []
        assert calls == [1]
    engine.dispose()


def test_feed_failure_reuses_cache_and_backs_off(monkeypatch):
    calls = []

    def fetch():
        calls.append(1)
        if len(calls) > 1:
            raise OSError("offline")
        return (google_trends.Trend("เทรนด์ทดสอบ", None, "100+"),)

    monkeypatch.setattr(google_trends, "fetch_feed", fetch)
    cache = google_trends.FeedCache()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first, stale = cache.get(now)
    assert not stale
    assert cache.get(now + timedelta(minutes=10)) == (first, True)
    assert cache.get(now + timedelta(minutes=10, seconds=30)) == (first, True)
    assert calls == [1, 1]
    with pytest.raises(google_trends.FeedError, match="temporarily unavailable"):
        cache.get(now + timedelta(days=2))
    assert len(calls) == 3
    with pytest.raises(google_trends.FeedError, match="Unexpected RSS declaration"):
        google_trends.parse_feed(b'<!DOCTYPE rss [<!ENTITY example "example">]><rss/>')
