from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.catalog.products import ChannelLink, Product
from app.core.auth import WorkspaceContext, require_workspace
from app.core.db import Base, get_db
from app.core.models import Organization
from app.insights.affiliate_reports import router

CLICK_CSV = """รหัสคลิก,เวลาคลิก,ภาคที่คลิก,Sub_id,อ้างอิง
C1,2026-11-20 08:00:00,Thailand,fbcloth01----,https://l.facebook.com/
C2,20-11-2569 12:00:00,Thailand,other-id----,https://www.tiktok.com/
C3,2026-11-19T19:00:00Z,Thailand,,direct
C1,2026-11-20 08:00:00,Thailand,fbcloth01----,https://l.facebook.com/
"""
ORDERS_CSV = """Order ID,Order Time,Item ID,Model ID,Order Status,Order Total Commission (THB),Item Commission (THB),Sub_id1,Sub_id2,Channel,Last Update Time
O1,2026-11-20 09:00:00,0001,V1,Pending,10.125000,4,fbcloth01,sale,,2026-11-20 12:00:00
O1,2026-11-20 09:00:00,0002,V2,Pending,10.125000,6,fbcloth01,sale,,2026-11-20 12:00:00
O2,2026-11-20 10:00:00,0001,V1,Cancelled,,999,fbcloth01,,,2026-11-20 12:00:00
O3,2026-11-21 10:00:00,0003,V1,Completed,,3.125,other-id,,TikTok,2026-11-21 12:00:00
O3,2026-11-21 10:00:00,0003,V2,Completed,,2.875,other-id,,TikTok,2026-11-21 12:00:00
"""


def test_import_real_report_shapes_and_reconcile_overlapping_exports():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    with session.begin() as db:
        db.add_all([Organization(id="ws-a", name="A"), Organization(id="ws-b", name="B")])
        db.add(Product(id="p-a", workspace_id="ws-a", name="Cloth", source_url="https://shop.example/a"))
        db.add(ChannelLink(workspace_id="ws-a", product_id="p-a", channel="facebook",
                           sub_id="fbcloth01", affiliate_url="https://s.shopee.co.th/example"))

    def db_session():
        with session() as db:
            yield db

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides.update({
        get_db: db_session,
        require_workspace: lambda workspace_id: WorkspaceContext(workspace_id, "owner", "owner"),
    })
    path = "/api/v1/workspaces/ws-a/affiliate-reports"

    with TestClient(app) as client:
        def upload(kind, body):
            return client.post(path + "/import/" + kind, files={"file": ("report.csv", body, "text/csv")})

        assert client.get(path).json() == {"sources": {}, "days": []}
        assert upload("orders", CLICK_CSV).status_code == 422
        assert upload("clicks", CLICK_CSV.encode("utf-16")).json() == {
            "kind": "clicks", "rows": 4, "saved": 3, "skipped": 1,
        }
        assert upload("clicks", CLICK_CSV.encode("cp874")).json()["saved"] == 0
        invalid = CLICK_CSV + "C4,not-a-day,Thailand,fbcloth01,facebook\n"
        assert upload("clicks", invalid).status_code == 422
        assert sum(row["clicks"] for row in client.get(path).json()["days"]) == 3

        assert upload("orders", ORDERS_CSV.encode("utf-8-sig")).json()["saved"] == 5
        assert upload("orders", ORDERS_CSV).json()["saved"] == 0
        pending = next(row for row in client.get(path).json()["days"] if row["sub_id"] == "fbcloth01-sale")
        assert (pending["estimated"], pending["confirmed"], pending["orders"]) == (10.125, 0, 1)
        assert pending["channel"] == "facebook" and pending["product_id"] == "p-a"

        # A later snapshot can confirm the same order, without creating a second order or commission.
        latest = ORDERS_CSV.replace("Pending", "Completed").replace("2026-11-20 12:00:00", "2026-11-22 12:00:00")
        assert upload("orders", latest).json()["saved"] == 3
        assert upload("orders", ORDERS_CSV).json()["saved"] == 0

        report = client.get(path).json()
        assert report["sources"]["clicks"] == {"first": "2026-11-20", "last": "2026-11-20"}
        assert {row["channel"] for row in report["days"]} == {"facebook", "tiktok", "unknown"}
        assert sum(row["orders"] for row in report["days"]) == 3
        assert sum(Decimal(str(row["estimated"])) for row in report["days"]) == Decimal("16.125")
        assert sum(Decimal(str(row["confirmed"])) for row in report["days"]) == Decimal("16.125")
        assert client.get(path, params={"start": "2026-11-21", "end": "2026-11-21"}).json()["days"] == [{
            "date": "2026-11-21", "channel": "tiktok", "sub_id": "other-id", "product_id": None,
            "clicks": 0, "orders": 1, "estimated": 6, "confirmed": 6,
        }]
        other = "/api/v1/workspaces/ws-b/affiliate-reports"
        assert client.get(other).json() == {"sources": {}, "days": []}
