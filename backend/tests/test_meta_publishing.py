from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.catalog.products import ChannelLink, Product
from app.content.renders import Render
from app.core.auth import WorkspaceContext, require_workspace
from app.core.config import Settings, get_settings
from app.core.db import Base, get_db
from app.core.models import Organization
from app.publishing import meta_publishing
from app.publishing.meta_graph import MetaError


class FakePage:
    page_id = "101"
    published = False
    comment_message = None

    def __init__(self):
        self.writes = []

    def graph(self, edge, *, params=None, form=None):
        if form is None:
            assert edge == "me"
            return {"id": self.page_id}
        self.writes.append((edge, form))
        if edge == "101/video_reels" and form["upload_phase"] == "start":
            return {"video_id": "202", "upload_url": "https://rupload.facebook.com/video-upload/202"}
        if edge == "101/video_reels" and form["upload_phase"] == "finish":
            self.published = True
            raise MetaError("finish response was lost")
        assert edge == "202/comments"
        self.comment_message = form["message"]
        return {"id": "202_404"}

    def upload(self, url, video_id, video):
        assert url.endswith("/202") and video_id == "202" and video == b"mp4"

    def reel(self, video_id):
        assert video_id == "202"
        return {
            "id": "202", "from": {"id": self.page_id, "name": "Studio test Page"},
            "status": {"publishing_phase": {"publish_status": "published" if self.published else None}},
        }

    def comments(self, video_id, pages=1):
        assert video_id == "202"
        if self.comment_message:
            yield {
                "id": "303_404", "from": {"id": self.page_id, "name": "Studio test Page"},
                "message": self.comment_message, "is_hidden": False,
            }


def test_live_flow_reconciles_lost_finish_and_alternate_comment_id(monkeypatch, tmp_path):
    provider = FakePage()
    monkeypatch.setattr(meta_publishing, "MetaGraph", lambda settings: provider)
    monkeypatch.setenv("RENDER_ROOT", str(tmp_path))
    artifact = tmp_path / "render-a" / "preview.mp4"
    artifact.parent.mkdir()
    artifact.write_bytes(b"mp4")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    with testing_session() as db:
        db.add(Organization(id="ws-a", name="A"))
        db.add(Product(
            id="product-a", workspace_id="ws-a", name="Lamp", source_url="https://shop.example/item",
            affiliate_url="https://s.shopee.co.th/legacy", image_rights_note="Seller photo permitted",
        ))
        db.add(ChannelLink(
            workspace_id="ws-a", product_id="product-a", channel="facebook",
            affiliate_url="https://s.shopee.co.th/facebook",
        ))
        db.add(Render(
            id="render-a", product_id="product-a", workspace_id="ws-a", status="completed",
            video_relpath="render-a/preview.mp4",
        ))
        db.commit()

    def db_session():
        with testing_session() as db:
            yield db

    settings = Settings(
        meta_test_page_id="101", meta_page_access_token=SecretStr("fake"),
        meta_studio_workspace_id="ws-a", meta_studio_publish_enabled=False,
    )
    app = FastAPI()
    app.include_router(meta_publishing.router)
    app.dependency_overrides.update({
        get_db: db_session, get_settings: lambda: settings,
        require_workspace: lambda: WorkspaceContext("ws-a", "owner-a", "owner"),
    })
    root = "/api/v1/workspaces/ws-a/publishing/meta"
    endpoint = root + "/publications/render-a"
    payload = {"render_id": "render-a", "caption": "A test Reel", "ai_generated": True}

    with TestClient(app) as client:
        assert client.post(root + "/publications", json=payload).status_code == 403
        assert client.get(root + "/reels/202").is_success
        assert provider.writes == []
        settings.meta_studio_publish_enabled = True

        def publish():
            return client.post(root + "/publications", json=payload).json()

        assert publish()["stage"] == "finish_requested"
        assert publish()["video_id"] == "202"
        assert client.get(endpoint).json()["can_post_comment"]
        assert len(provider.writes) == 2
        assert provider.writes[1][1]["is_ai_generated"] == "true"

        comment = client.post(endpoint + "/comment").json()
        assert comment["comment_id"] == "202_404"
        assert comment["reel"]["comment_verified"]
        assert comment["reel"]["comments"][0]["id"] == "303_404"
        assert "https://s.shopee.co.th/facebook" in provider.comment_message
        assert client.post(endpoint + "/comment").json()["reel"]["comment_verified"]
        assert len(provider.writes) == 3

        app.dependency_overrides[require_workspace] = lambda: WorkspaceContext("ws-b", "owner-b", "owner")
        assert client.get(root + "/reels/202").status_code == 403
    engine.dispose()
