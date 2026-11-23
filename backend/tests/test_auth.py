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


def test_purchase_preview_collects_assets_without_creating_publishable_render(client, tmp_path, monkeypatch):
    from io import BytesIO

    from PIL import Image

    monkeypatch.setenv("RENDER_ROOT", str(tmp_path))
    token = register(client)
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    scope = f"/api/v1/workspaces/{workspace}"
    endpoint = scope + "/purchase-previews"
    purchase = {
        "name": "Bottle", "product_url": "https://shopee.co.th/product/123/456",
        "shopee_image": "https://down-th.img.susercontent.com/file/example",
        "search_images": ["https://cdn.hstatic.net/products/one.jpg",
                          "https://www.potterscookshop.co.uk/cdn/shop/files/two.jpg"],
        "purchase_confirmed": True,
    }
    assert client.get(endpoint, headers=headers).json() == []
    assert client.post(endpoint, headers=headers, json={**purchase, "purchase_confirmed": False}).status_code == 422
    assert client.post(endpoint, headers=headers, json={
        **purchase, "shopee_image": "https://not-shopee.example/file/one",
    }).status_code == 422
    saved = client.post(endpoint, headers=headers, json=purchase).raise_for_status().json()
    assert saved["purchase_status"] == "confirmed_completed"

    def collect(url, source):
        colors = {purchase["shopee_image"]: "navy", purchase["search_images"][0]: "olive",
                  purchase["search_images"][1]: "green"}
        image = Image.new("RGB", (320, 480), colors[url])
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        return buffer.getvalue(), image.convert("RGBA"), "jpg"

    monkeypatch.setattr("app.purchase_previews.fetch_image", collect)
    monkeypatch.setattr("app.purchase_previews._render", lambda inputs, output, scenes: output.write_bytes(b"mp4"))
    item = endpoint + "/" + saved["id"]
    preview = client.post(item + "/render", headers=headers).raise_for_status().json()
    assert [asset["source"] for asset in preview["assets"]] == ["google", "shopee", "google"]
    directory = tmp_path / "Asset" / workspace / saved["id"] / "runs" / preview["id"]
    assert all((directory / asset["file"]).is_file() for asset in preview["assets"])
    assert client.get(endpoint, headers=headers).json()[0]["preview"] == preview
    video = item + "/video/" + preview["id"]
    assert client.get(video, headers=headers).content == b"mp4"
    other = {"Authorization": f"Bearer {register(client, 'other@example.com')}"}
    assert client.get(video, headers=other).status_code == 404
    assert client.get(video).status_code == 401
    assert client.get(scope + "/renders", headers=headers).json() == []

    collected = client.post(endpoint + "/collect-and-render", headers=headers, json={
        **purchase, "purchase_source": "shopee_completed", "search_source": "google_images",
        "scene_crops": [None, None, [0.1, 0.1, 0.9, 0.9]],
    }).raise_for_status().json()
    assert collected["purchase_source"] == "shopee_completed"
    assert collected["preview"]["id"] != preview["id"]
    assert (directory.parent / collected["preview"]["id"] / "sources.json").is_file()
    assert client.get(video, headers=headers).content == b"mp4"
    flow = item + "/flow-preview"
    assert client.post(flow, headers=headers, files={"clip": ("clip.mov", b"test", "video/quicktime")}).status_code == 422

    def render_flow(opener, photos, output, name, opening_text, *, product_first=False):
        assert opener.read_bytes() == b"local MP4"
        assert len(photos) == (3 if product_first else 2) and all(photo.is_file() for photo in photos)
        assert opening_text == "ขวดน้ำพกไปทำงาน"
        output.write_bytes(b"composite")
        return 4.0

    monkeypatch.setattr("app.purchase_previews.render_flow_preview", render_flow)
    photo_first = client.post(
        flow, headers=headers, data={"opening_text": "ขวดน้ำพกไปทำงาน", "product_first": "true"},
        files={"clip": ("clip.mp4", b"local MP4", "video/mp4")},
    ).raise_for_status().json()
    assert photo_first["opening"]["starts_at"] == 4
    assert len(photo_first["assets"]) == 3
    combined = client.post(
        flow, headers=headers, data={"opening_text": "ขวดน้ำพกไปทำงาน"},
        files={"clip": ("clip.mp4", b"local MP4", "video/mp4")},
    ).raise_for_status().json()
    assert combined["opening"] == {"source": "google_flow", "file": "flow-opening.mp4", "seconds": 4,
                                   "text": "ขวดน้ำพกไปทำงาน"}
    assert len(combined["assets"]) == 2
    assert client.get(item + "/video/" + combined["id"], headers=headers).content == b"composite"
    assert client.get(scope + "/renders", headers=headers).json() == []


def test_pipeline_scoping_and_idempotency(client: TestClient, tmp_path, monkeypatch):
    from io import BytesIO

    from PIL import Image

    monkeypatch.setenv("RENDER_ROOT", str(tmp_path))
    monkeypatch.setattr("app.renders._render", lambda inputs, output, scenes: output.write_bytes(b"mp4"))

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


def test_shopee_offer_snapshots_are_validated_updated_and_workspace_scoped(client: TestClient):
    token = register(client)
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    path = f"/api/v1/workspaces/{workspace}/shopee-offers"
    offer = {
        "offer_id": "43314705287", "name": "กล่องติดผนัง", "sold": 2000,
        "sold_is_minimum": True, "price_satang": 6200, "commission_bps": 500,
    }
    assert client.post(path, headers=headers, json={"offers": [offer]}).json() == {"saved": 1}
    image = "https://down-th.img.susercontent.com/file/sg-example"
    assert client.post(path, headers=headers, json={
        "offers": [{**offer, "image_url": image}],
    }).status_code == 200
    assert client.post(path, headers=headers, json={
        "offers": [offer, {**offer, "commission_bps": 625}],
    }).json() == {"saved": 1}
    invalid = client.post(path, headers=headers, json={"offers": [{**offer, "sold": -1}]})
    assert invalid.status_code == 422
    bad_image = client.post(path, headers=headers, json={
        "offers": [{**offer, "image_url": "https://example.org/image.jpg"}],
    })
    assert bad_image.status_code == 422
    rows = client.get(path, headers=headers).json()
    assert len(rows) == 1
    assert rows[0]["commission_bps"] == 625 and rows[0]["sold_is_minimum"] is True
    assert rows[0]["observed_at"].endswith("Z")
    assert rows[0]["image_url"] == image
    other_headers = {"Authorization": f"Bearer {register(client, 'other@example.com')}"}
    assert client.get(path, headers=other_headers).status_code == 404


def test_reel_accepts_ordered_footage_with_more_than_three_photos(client, tmp_path, monkeypatch):
    import json
    import shutil
    import subprocess
    from io import BytesIO

    from PIL import Image

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and ffprobe are required for mixed media verification")

    token = register(client)
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    scope = f"/api/v1/workspaces/{workspace}"
    product = client.post(scope + "/products", headers=headers, json={
        "name": "Local test product", "source_url": "https://example.com/mixed-media",
        "image_rights_note": "Generated test assets",
    }).raise_for_status().json()
    monkeypatch.setenv("RENDER_ROOT", str(tmp_path / "renders"))

    clip = tmp_path / "demo.mov"
    subprocess.run([
        "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x568:rate=30",
        "-t", "3", "-c:v", "libx264", str(clip),
    ], check=True)
    clip_upload = ("media", (clip.name, clip.read_bytes(), "video/quicktime"))
    photos = []
    for index, color in enumerate(("red", "blue", "green", "yellow", "cyan", "magenta")):
        buffer = BytesIO()
        Image.new("RGB", (240, 160), color).save(buffer, format="PNG")
        photos.append(("media", (f"angle-{index}.png", buffer.getvalue(), "image/png")))

    route = scope + "/renders"
    data = {"product_id": product["id"]}
    assert client.post(route, headers=headers, files=[clip_upload], data=data).status_code == 422
    assert client.post(route, headers=headers, files=photos[:3], data=data).status_code == 422
    render = client.post(route, headers=headers, files=[clip_upload, *photos], data=data)
    saved = render.raise_for_status().json()
    assert saved["status"] == "completed"
    file = tmp_path / "renders" / saved["id"] / "preview.mp4"
    metadata = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=nb_frames,width,height", "-of", "json", str(file),
    ], check=True, capture_output=True, text=True)
    stream = json.loads(metadata.stdout)["streams"][0]
    assert stream == {"width": 1080, "height": 1920, "nb_frames": "450"}

    def read_frame(seconds):
        return subprocess.run([
            "ffmpeg", "-v", "error", "-ss", str(seconds), "-i", str(file),
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-",
        ], check=True, capture_output=True).stdout

    assert read_frame(0) != read_frame(1)
    with Image.open(BytesIO(read_frame(14.5))) as last:
        red, green, blue = last.convert("RGB").getpixel((540, 960))
        assert red > 235 and green < 20 and blue > 235
    assert client.get(f"{route}/{saved['id']}/video", headers=headers).content == file.read_bytes()

    plan = {
        "duration_s": 15, "status": "ready_for_preview", "format": "PRODUCT_WALKTHROUGH",
        "scenes": [
            {"start_s": 0, "end_s": 2, "source": "REAL_PHOTO", "asset_id": "A3", "subtitle_th": "ภาพจริง"},
            {"start_s": 2, "end_s": 3, "source": "REAL_VIDEO", "asset_id": "A1", "source_range_s": [1, 2]},
            {"start_s": 3, "end_s": 15, "source": "REAL_PHOTO", "asset_id": "A2"},
        ],
    }
    invalid = {**plan, "scenes": [{**plan["scenes"][0], "asset_id": "A12"}, *plan["scenes"][1:]]}
    result = client.post(route, headers=headers, files=[clip_upload, *photos[:2]],
                         data={**data, "reel_plan": json.dumps(invalid)})
    assert result.status_code == 422 and "A12" in result.json()["detail"]
    result = client.post(route, headers=headers, files=[clip_upload, *photos[:2]],
                         data={**data, "reel_plan": json.dumps(plan)})
    planned = result.raise_for_status().json()
    assert planned["status"] == "completed"
    file = tmp_path / "renders" / planned["id"] / "preview.mp4"
    with Image.open(BytesIO(read_frame(1))) as first:
        red, green, blue = first.convert("RGB").getpixel((540, 960))
        assert blue > 235 and red < 20 and green < 20
        assert sum(first.convert("L").crop((110, 1530, 970, 1660)).histogram()[220:]) > 200
    with Image.open(BytesIO(read_frame(4))) as last:
        red, green, blue = last.convert("RGB").getpixel((540, 960))
        assert red > 235 and green < 20 and blue < 20
        assert sum(last.convert("L").crop((110, 1530, 970, 1660)).histogram()[220:]) == 0

    reference = subprocess.run([
        "ffmpeg", "-v", "error", "-ss", "1.4", "-i", str(clip), "-frames:v", "1",
        "-f", "image2pipe", "-vcodec", "png", "-",
    ], check=True, capture_output=True).stdout
    from PIL import ImageChops, ImageStat

    with Image.open(BytesIO(read_frame(2.4))) as selected, Image.open(BytesIO(reference)) as original:
        difference = ImageChops.difference(selected.convert("RGB").resize(original.size), original.convert("RGB"))
        assert max(ImageStat.Stat(difference).mean) < 12


def test_storyboard_roundtrip_and_workspace_isolation(client: TestClient, monkeypatch, tmp_path):
    import json
    from io import BytesIO

    from PIL import Image

    monkeypatch.setenv("RENDER_ROOT", str(tmp_path))
    owner = {"Authorization": f"Bearer {register(client)}"}
    outsider = {"Authorization": f"Bearer {register(client, 'outside@example.com')}"}
    owner_id = client.get("/api/v1/workspaces", headers=owner).json()[0]["id"]
    outsider_id = client.get("/api/v1/workspaces", headers=outsider).json()[0]["id"]
    workspace = f"/api/v1/workspaces/{owner_id}"
    path = f"{workspace}/storyboards"
    offer = {
        "offer_id": "123", "name": "ผ้าถูพื้นแพ็ก 5 ห่อ", "sold": 500,
        "sold_is_minimum": True, "price_satang": 5900, "commission_bps": 800,
    }
    client.post(f"{workspace}/shopee-offers", headers=owner, json={"offers": [offer]}).raise_for_status()

    output = BytesIO()
    Image.new("RGB", (90, 160), "white").save(output, "PNG")
    pixels = output.getvalue()
    upload = ("photo.png", pixels, "image/png")
    plan = {
        "source": "offer", "source_id": "123", "variant": "แพ็กเปียก 5 ห่อ",
        "verified_details": "ด้านหน้าและจำนวนห่อจากรูปอ้างอิง",
        "scenes": [{"seconds": 4, "action": "ภาพฉลาก", "dialogue": ""}],
    }
    refs = {"product": upload, "presenter": upload}
    response = client.post(path, headers=owner, data={"plan": json.dumps(plan)}, files=refs)
    assert response.status_code == 201
    created = response.json()
    assert created["product_name"] == offer["name"]
    assert client.get(path, headers=owner).json() == [created]

    item = f"{path}/{created['id']}"
    result = client.get(f"{item}/files/product", headers=owner)
    assert result.headers["content-type"] == "image/png"
    assert result.content == pixels
    assert client.get(f"{item}/files/board", headers=owner).status_code == 404
    assert client.put(f"{item}/image", headers=owner, files={"image": upload}).status_code == 200
    assert client.get(path, headers=owner).json()[0]["files"]["board"] == "storyboard-from-flow.png"

    fake_upload = ("video.png", b"<svg onload='alert(1)'/>", "image/png")
    assert client.put(f"{item}/image", headers=owner, files={"image": fake_upload}).status_code == 422
    assert client.get(f"{item}/files/board", headers=owner).content == pixels

    other_path = f"/api/v1/workspaces/{outsider_id}/storyboards"
    assert client.get(path, headers=outsider).status_code == 404
    assert client.get(other_path, headers=outsider).json() == []
    other_item = f"{other_path}/{created['id']}"
    assert client.put(f"{other_item}/image", headers=outsider, files={"image": upload}).status_code == 404
    assert client.get(f"{other_item}/files/product", headers=outsider).status_code == 404
    assert client.post(other_path, headers=outsider, data={"plan": json.dumps(plan)}, files=refs).status_code == 404
