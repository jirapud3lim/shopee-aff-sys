from collections.abc import Generator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import require_workspace
from app.db import Base, get_db
from app.main import app
from app.models import SessionToken, User


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    probe = FastAPI()
    probe.include_router(app.router)
    probe.dependency_overrides.update(app.dependency_overrides)

    @probe.get("/api/v1/workspaces/{workspace_id}/probe")
    def protected_probe(context=Depends(require_workspace)):
        return {"workspace_id": context.workspace_id, "role": context.role}

    with TestClient(probe) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register(client: TestClient, email: str = "person@example.com") -> str:
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "long-test-password-42"}
    )
    assert response.status_code == 201
    return response.json()["token"]


def test_register_login_and_persist_only_token_digest(client: TestClient):
    token = register(client)
    assert token
    workspaces = client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert workspaces.status_code == 200
    assert len(workspaces.json()) == 1
    assert workspaces.json()[0]["role"] == "owner"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "PERSON@example.com", "password": "long-test-password-42"},
    )
    assert login.status_code == 200
    assert login.json()["token"] != token

    db_override = app.dependency_overrides[get_db]
    db = next(db_override())
    try:
        row = db.query(SessionToken).first()
        user = db.query(User).first()
        assert row is not None and row.token_hash != token
        assert user is not None and user.password_hash != "long-test-password-42"
    finally:
        db.close()


def test_logout_revokes_only_presented_session(client: TestClient):
    token = register(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/workspaces", headers=headers).status_code == 401


def test_invalid_password_and_missing_membership_are_denied(client: TestClient):
    token = register(client)
    failed = client.post(
        "/api/v1/auth/login", json={"email": "person@example.com", "password": "wrong-password"}
    )
    assert failed.status_code == 401

    own = client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}).json()[0][
        "id"
    ]
    assert (
        client.get(
            f"/api/v1/workspaces/{own}/probe", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/v1/workspaces/00000000-0000-0000-0000-000000000000/probe",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 404
    )


def test_pipeline_scoping_and_idempotency(client: TestClient, tmp_path, monkeypatch):
    from io import BytesIO

    from PIL import Image

    monkeypatch.setenv("RENDER_ROOT", str(tmp_path))
    monkeypatch.setattr("app.renders._render", lambda inputs, output: output.write_bytes(b"mp4"))

    first = {"Authorization": f"Bearer {register(client, 'first@example.com')}"}
    second = {"Authorization": f"Bearer {register(client, 'second@example.com')}"}
    workspace = client.get("/api/v1/workspaces", headers=first).json()[0]["id"]
    second_workspace = client.get("/api/v1/workspaces", headers=second).json()[0]["id"]
    scope = f"/api/v1/workspaces/{workspace}"
    other_scope = f"/api/v1/workspaces/{second_workspace}"
    product = client.post(
        scope + "/products",
        headers=first,
        json={
            "name": "Local fixture",
            "source_url": "https://shop.example/product",
            "affiliate_url": "https://shop.example/affiliate",
            "image_rights_note": "Original synthetic images",
        },
    ).json()
    image = BytesIO()
    Image.new("RGB", (16, 16), "green").save(image, format="PNG")
    files = [
        ("images", (f"sample-{index}.png", image.getvalue(), "image/png")) for index in range(3)
    ]
    response = client.post(
        scope + "/renders", headers=first, data={"product_id": product["id"]}, files=files
    )
    assert response.status_code == 201
    render = response.json()
    assert render["status"] == "completed"
    assert (
        client.get(other_scope + f"/renders/{render['id']}/video", headers=second).status_code
        == 404
    )
    assert client.get(scope + f"/renders/{render['id']}/video", headers=first).content == b"mp4"

    payload = {"render_id": render["id"], "caption": "Local simulation", "include_comment": True}
    assert (
        client.post(
            other_scope + "/publishing/simulations", headers=second, json=payload
        ).status_code
        == 404
    )
    route = scope + "/publishing/simulations"
    response = client.post(route, headers=first, json=payload)
    assert response.status_code == 201
    simulation = response.json()
    assert simulation["provider"] == "simulated"
    assert (
        simulation["video_status"],
        simulation["comment_status"],
        simulation["comment_verified"],
    ) == (
        "published",
        "posted",
        True,
    )
    assert [item["outcome"] for item in simulation["attempts"] if item["phase"] == "finish"] == [
        "ambiguous"
    ]
    replay = client.post(route, headers=first, json=payload)
    assert replay.status_code == 200
    assert replay.json() == simulation
    assert (
        client.post(route, headers=first, json={**payload, "caption": "Changed"}).status_code == 409
    )
