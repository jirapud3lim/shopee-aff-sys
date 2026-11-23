from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import require_workspace
from app.db import Base, get_db
from app.models import Organization  # register organizations table before create_all
from app.products import router


@dataclass
class Context:
    workspace_id: str
    user_id: str = "user-a"
    role: str = "owner"


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    session.add_all(
        [Organization(id="workspace-a", name="A"), Organization(id="workspace-b", name="B")]
    )
    session.commit()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[require_workspace] = lambda: Context("workspace-a")
    with TestClient(app) as test_client:
        yield test_client
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_manual_create_list_and_workspace_scoped_lookup(client):
    response = client.post(
        "/api/v1/workspaces/workspace-a/products",
        json={
            "name": "  Lamp  ",
            "source_url": "https://SHOP.example/item/1/",
            "affiliate_url": "https://affiliate.example/1",
            "image_rights_note": "Seller provided image; permission recorded",
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Lamp"
    assert created["source_url"] == "https://shop.example/item/1"
    assert created["image_rights_note"]
    assert client.get("/api/v1/workspaces/workspace-a/products").json() == [created]

    app = client.app
    app.dependency_overrides[require_workspace] = lambda: Context("workspace-b")
    assert client.get(f"/api/v1/workspaces/workspace-b/products/{created['id']}").status_code == 404


def test_canonical_url_duplicate_is_conflict(client):
    url = "/api/v1/workspaces/workspace-a/products"
    assert (
        client.post(
            url, json={"name": "One", "source_url": "https://shop.example/p/1/"}
        ).status_code
        == 201
    )
    duplicate = client.post(url, json={"name": "Again", "source_url": "https://SHOP.example/p/1"})
    assert duplicate.status_code == 409


def test_csv_import_reports_duplicate_and_bad_rows(client):
    response = client.post(
        "/api/v1/workspaces/workspace-a/products/import",
        files={
            "file": (
                "products.csv",
                "name,source_url,affiliate_url,image_rights_note\n"
                "Good,https://shop.example/good,,rights\n"
                "Duplicate,https://shop.example/good,,\n"
                "Bad,not-a-url,,\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["imported"] == 1
    assert len(result["duplicates"]) == 1
    assert len(result["errors"]) == 1
    assert result["total_rows"] == 3


def test_csv_import_requires_headers(client):
    response = client.post(
        "/api/v1/workspaces/workspace-a/products/import",
        files={"file": ("products.csv", "title,url\nLamp,https://shop.example/lamp\n", "text/csv")},
    )
    assert response.status_code == 422


def test_csv_extra_column_reports_error_and_preserves_valid_rows(client):
    response = client.post(
        "/api/v1/workspaces/workspace-a/products/import",
        files={
            "file": (
                "products.csv",
                "name,source_url\n"
                "Malformed,https://shop.example/bad,extra\n"
                "Valid,https://shop.example/valid\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 1
    assert response.json()["errors"] == [{"row": 2, "error": "Unexpected extra column"}]


def test_csv_import_100_products_replay_and_workspace_isolation(client):
    path = "/api/v1/workspaces/workspace-a/products"
    csv = "name,source_url\n" + "".join(
        f"Product {n},https://shop.example/products/{n}\n" for n in range(100)
    )
    files = {"file": ("products.csv", csv, "text/csv")}
    first = client.post(path + "/import", files=files)
    assert first.status_code == 200
    assert first.json() == {"imported": 100, "duplicates": [], "errors": [], "total_rows": 100}

    replay = client.post(path + "/import", files=files)
    assert replay.status_code == 200
    assert replay.json()["imported"] == 0
    assert len(replay.json()["duplicates"]) == 100
    assert len(client.get(path).json()) == 100

    client.app.dependency_overrides[require_workspace] = lambda: Context("workspace-b")
    assert client.get("/api/v1/workspaces/workspace-b/products").json() == []


def test_csv_channel_link_and_workspace_isolation(client):
    path = "/api/v1/workspaces/workspace-a/products"
    csv_data = (
        "name,source_url,affiliate_url,affiliate_channel,affiliate_sub_id\n"
        "Wipes,https://shop.example/wipes,https://affiliate.example/facebook,facebook,fb01\n"
        "Spray,https://shop.example/spray,,facebook,fb02\n"
    )
    result = client.post(path + "/import", files={"file": ("draft.csv", csv_data, "text/csv")})
    assert result.status_code == 200
    assert result.json()["imported"] == 1
    assert len(result.json()["errors"]) == 1

    product = client.get(path).json()[0]
    assert product["affiliate_url"] is None
    links = f"{path}/{product['id']}/channel-links"
    instagram = {"affiliate_url": "https://affiliate.example/ig", "sub_id": "ig01"}
    assert client.put(links + "/instagram", json=instagram).status_code == 200
    assert client.put(links + "/instagram", json={**instagram, "sub_id": "ig02"}).status_code == 200
    assert client.get(links).json() == [
        {
            "channel": "facebook",
            "affiliate_url": "https://affiliate.example/facebook",
            "sub_id": "fb01",
        },
        {"channel": "instagram", **instagram, "sub_id": "ig02"},
    ]

    fallback = "https://affiliate.example/default"
    assert client.patch(f"{path}/{product['id']}", json={"affiliate_url": fallback}).status_code == 200
    index = path + "/affiliate-links"
    shared = {"product_id": product["id"], "product_name": "Wipes"}
    assert client.get(index).raise_for_status().json() == [
        {**shared, "channel": "facebook", "sub_id": "fb01", "affiliate_url": "https://affiliate.example/facebook"},
        {**shared, "channel": "instagram", "sub_id": "ig02", "affiliate_url": instagram["affiliate_url"]},
        {**shared, "channel": None, "sub_id": None, "affiliate_url": fallback},
    ]

    client.app.dependency_overrides[require_workspace] = lambda: Context("workspace-b")
    other = links.replace("workspace-a", "workspace-b")
    assert client.get(other).status_code == 404
    assert client.put(other + "/facebook", json=instagram).status_code == 404
    assert client.get(index.replace("workspace-a", "workspace-b")).raise_for_status().json() == []
