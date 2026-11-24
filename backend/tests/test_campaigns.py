from datetime import datetime, timezone
from time import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.catalog.products import Product
from app.content.renders import Render
from app.core.auth import WorkspaceContext, require_workspace
from app.core.config import Settings, get_settings
from app.core.db import Base, get_db
from app.core.models import Organization, OrganizationMember, User
from app.publishing import campaign_worker
from app.publishing.campaigns import CampaignItem, CampaignWorkerState, router
from app.publishing.meta_publishing import MetaPublication


def test_campaign_schedule_pause_resume_reconciliation_and_isolation(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setenv("RENDER_ROOT", str(tmp_path))
    with session.begin() as db:
        db.add_all([Organization(id="ws-a", name="A"), Organization(id="ws-b", name="B"),
                    User(id="owner", email="owner@example.com", password_hash="unused")])
        db.flush()
        db.add_all([OrganizationMember(organization_id="ws-a", user_id="owner", role="owner"),
                    OrganizationMember(organization_id="ws-b", user_id="owner", role="owner"),
                    CampaignWorkerState(id=1, lease_until=0, next_live_dispatch_at=0),
                    Product(id="product", workspace_id="ws-a", name="Cloth",
                            source_url="https://example.com/p", affiliate_url="https://example.com/aff",
                            image_rights_note="Original art")])
        db.flush()
        for render_id in ("render-a", "render-b"):
            db.add(Render(id=render_id, product_id="product", workspace_id="ws-a", status="completed",
                          video_relpath=f"{render_id}/preview.mp4"))
            artifact = tmp_path / render_id / "preview.mp4"
            artifact.parent.mkdir()
            artifact.write_bytes(b"test")

    def db_session():
        with session() as db:
            yield db

    settings = Settings(meta_test_page_id="101", meta_studio_workspace_id="ws-a",
                        meta_page_access_token=SecretStr("fixture"), meta_studio_publish_enabled=True)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides.update({
        get_db: db_session, get_settings: lambda: settings,
        require_workspace: lambda workspace_id: WorkspaceContext(workspace_id, "owner", "owner"),
    })
    path = "/api/v1/workspaces/ws-a/campaigns"
    now = int(time())

    def item(render_id, epoch):
        return {"render_id": render_id, "caption": "Test Reel",
                "scheduled_at": datetime.fromtimestamp(epoch, timezone.utc).isoformat()}

    def tick(epoch):
        # Every tick opens a new session, including after the simulated worker restart.
        with session() as db:
            return campaign_worker.tick(db, settings, epoch)

    with TestClient(app) as client:
        payload = {"name": "Trial", "items": [item("render-a", now + 60), item("render-b", now + 120)]}
        assert client.post(path, json=payload | {"mode": "live"}).status_code == 403
        response = client.post(path, json=payload)
        assert response.status_code == 201
        campaign = response.json()
        assert campaign["state"] == "draft"
        action_path = f"{path}/{campaign['id']}/actions"
        assert not tick(now + 60)
        assert client.post(action_path.replace("ws-a", "ws-b"), json={"action": "activate"}).status_code == 404
        assert client.post(action_path, json={"action": "activate"}).is_success
        assert not tick(now + 59)
        assert client.post(action_path, json={"action": "pause"}).is_success
        assert not tick(now + 60)
        assert client.post(action_path, json={"action": "resume"}).is_success
        assert tick(now + 60)
        assert not tick(now + 61)
        assert client.post(action_path, json={"action": "cancel"}).is_success
        assert not tick(now + 120)
        jobs = client.get(path).json()["campaigns"][0]["items"]
        assert [job["state"] for job in jobs] == ["completed", "cancelled"]

        settings.campaign_live_enabled = True
        response = client.post(path, json={
            "name": "Mocked provider", "mode": "live",
            "items": [item("render-a", now + 600), item("render-b", now + 1200)],
        })
        assert response.status_code == 201
        campaign_id = response.json()["id"]
        assert client.post(f"{path}/{campaign_id}/actions", json={"action": "activate"}).is_success

        sends = []
        comments = []

        def publish(payload, context, db, settings):
            sends.append(payload.render_id)
            db.add(MetaPublication(
                workspace_id=context.workspace_id, render_id=payload.render_id, page_id="101",
                caption=payload.caption, comment_message="link", ai_generated=False,
                stage="finish_requested", video_id="500",
            ))
            db.commit()
            return {"video_id": "500", "stage": "finish_requested", "reel": None,
                    "error": "finish response timed out", "can_post_comment": False}

        def read(render_id, context, db, settings):
            return {"video_id": "500", "stage": "finish_requested", "error": None,
                    "can_post_comment": True, "reel": {"publish_status": "published",
                    "video_status": "ready", "url": "https://www.facebook.com/reel/500/",
                    "comment_verified": False, "comments": []}}

        def comment(render_id, context, db, settings):
            comments.append(render_id)
            result = read(render_id, context, db, settings)
            result["reel"]["comment_verified"] = True
            result["reel"]["comments"] = [{"url": "https://www.facebook.com/reel/500/?comment_id=600"}]
            return result

        monkeypatch.setattr(campaign_worker, "publish", publish)
        monkeypatch.setattr(campaign_worker, "publication", read)
        monkeypatch.setattr(campaign_worker, "post_comment", comment)

        assert tick(now + 600)
        assert not tick(now + 601)
        settings.campaign_live_enabled = False
        assert not tick(now + 615)
        settings.campaign_live_enabled = True
        with session.begin() as db:
            lease = db.get(CampaignWorkerState, 1)
            lease.lease_token = "stopped-worker"
            lease.lease_until = now + 620
        assert not tick(now + 619)
        assert tick(now + 620)
        assert not tick(now + 621)
        assert sends == ["render-a"]
        assert comments == ["render-a"]
        live = next(row for row in client.get(path).json()["campaigns"] if row["id"] == campaign_id)
        assert live["items"][0]["state"] == "completed"
        assert live["items"][0]["comment_url"].endswith("comment_id=600")
        assert live["items"][1]["state"] == "queued"
        assert client.get(path.replace("ws-a", "ws-b")).json()["campaigns"] == []
    engine.dispose()
