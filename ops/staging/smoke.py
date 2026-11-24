"""Verify staging wiring through the web proxy without connecting external providers."""

import argparse
import json
import os
import secrets
import struct
import subprocess
import time
import zlib
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

WEB = os.environ.get("STAGING_WEB_ORIGIN", "http://127.0.0.1:" + os.environ.get("STAGING_WEB_PORT", "3110"))
PROM = os.environ.get("STAGING_PROM_ORIGIN", "http://127.0.0.1:" + os.environ.get("STAGING_MONITOR_PORT", "19090"))


def fetch(origin, path, *, token=None, payload=None, content_type="application/json", expected=200, method=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if payload is not None:
        headers["Content-Type"] = content_type
        if content_type == "application/json":
            payload = json.dumps(payload).encode()
    request = Request(origin + path, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=180) as response:
            status, body = response.status, response.read()
    except HTTPError as exc:
        status, body = exc.code, exc.read()
    if status != expected:
        raise RuntimeError(f"{path}: expected HTTP {expected}, got {status}: {body[:500]!r}")
    return body


def api(path, **options):
    data = fetch(WEB, "/api/v1" + path, **options)
    return json.loads(data) if data else None


def eventually(check, label, *, limit=90):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {label}")


def png(color, width=8, height=8):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + bytes(color) * width) * height))
            + chunk(b"IEND", b""))


def multipart(*fields):
    boundary = secrets.token_hex(16)
    delimiter = b"--" + boundary.encode()
    parts = []
    for name, value, *file in fields:
        disposition = f'Content-Disposition: form-data; name="{name}"'
        if file:
            filename, content_type = file
            disposition += f'; filename="{filename}"\r\nContent-Type: {content_type}'
        parts.append(delimiter + b"\r\n" + disposition.encode() + b"\r\n\r\n" +
                     (value.encode() if isinstance(value, str) else value) + b"\r\n")
    body = b"".join(parts) + delimiter + b"--\r\n"
    return body, "multipart/form-data; boundary=" + boundary


def metric_value(query):
    response = fetch(PROM, "/api/v1/query?" + urlencode({"query": query}))
    values = json.loads(response)["data"]["result"]
    return float(values[0]["value"][1]) if values else 0


def verify_storyboard(scope, product, link, token):
    image = png((225, 204, 156), width=72, height=128)
    plan = {
        "source": "catalog", "source_id": product["id"], "variant": "Smoke fixture white",
        "verified_details": "Synthetic fixture", "affiliate": link,
        "scenes": [{"seconds": 5, "action": "Static test frame", "dialogue": ""}] * 3,
    }
    body, mime = multipart(("plan", json.dumps(plan)), ("product", image, "product.png", "image/png"),
                           ("presenter", image, "presenter.png", "image/png"))
    board = api(scope + "/storyboards", token=token, payload=body, content_type=mime, expected=201)
    assert board["affiliate"] == link and board["source_id"] == product["id"]
    path = scope + f"/storyboards/{board['id']}"
    body, mime = multipart(("image", image, "board.png", "image/png"))
    board = api(path + "/image", token=token, payload=body, content_type=mime, method="PUT")
    version = sha256(image).hexdigest()
    assert board["review_version"] == version and board["approved_scenes"] == []
    board = api(path + "/approval", token=token, payload={"version": version, "scenes": [1, 2, 3]},
                method="PUT")
    assert board["approved_scenes"] == [1, 2, 3]


def verify_reports(scope, product, sub_id, token):
    path = scope + "/affiliate-reports"
    for kind, csv in (
        ("clicks", "Click ID,Click Time,Sub_id,Referrer\n"
                   f"c-1,2026-11-20 08:00:00,{sub_id},https://l.facebook.com/\n"),
        ("orders", "Order ID,Order Time,Item ID,Order Status,Item Commission (THB),Sub_id1\n"
                   f"o-1,2026-11-20 09:00:00,456,Completed,12.5,{sub_id}\n"),
    ):
        body, mime = multipart(("file", csv, "report.csv", "text/csv"))
        for expected in (1, 0):
            result = api(f"{path}/import/{kind}", token=token, payload=body, content_type=mime)
            assert result["saved"] == expected, result
    row, = api(path, token=token)["days"]
    assert row == {"date": "2026-11-20", "channel": "facebook", "sub_id": sub_id,
                   "product_id": product["id"], "clicks": 1, "orders": 1, "estimated": 12.5, "confirmed": 12.5}


def verify_video(video):
    with TemporaryDirectory() as directory:
        path = Path(directory) / "fixture.mp4"
        path.write_bytes(video)
        report = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,codec_type,width,height:format=duration",
            "-of", "json", path,
        ])
        report = json.loads(report)
        picture, = (stream for stream in report["streams"] if stream["codec_type"] == "video")
        assert (picture["codec_name"], picture["width"], picture["height"]) == ("h264", 1080, 1920)
        assert abs(float(report["format"]["duration"]) - 15) < 0.1
        subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", path, "-f", "null", "-"], check=True)


def run(release=False):
    assert api("/health") == {"status": "ok"}
    fetch(WEB, "/")
    fetch(WEB, "/internal/metrics", expected=404)
    account = "staging-smoke-" + secrets.token_hex(6)
    token = api("/auth/register", payload={
        "email": account + "@example.com", "password": secrets.token_urlsafe(24),
    }, expected=201)["token"]
    workspace, = api("/workspaces", token=token)
    scope = "/workspaces/" + workspace["id"]
    status = api(scope + "/publishing/meta", token=token)
    assert not status["connected"] and not status["publish_enabled"]
    product = api(scope + "/products", token=token, expected=201, payload={
        "name": "Staging smoke product", "source_url": "https://shopee.co.th/product/123/456",
        "image_rights_note": "Generated smoke-test fixtures",
    })
    assert product in api(scope + "/products", token=token)
    sub_id = "fbsmoke" + secrets.token_hex(4)
    link = {"affiliate_url": "https://s.shopee.co.th/smoke-fixture", "sub_id": sub_id}
    path = scope + f"/products/{product['id']}/channel-links"
    saved = api(path + "/facebook", token=token, payload=link, method="PUT")
    assert saved == {"channel": "facebook", **link} and api(path, token=token) == [saved]
    verify_storyboard(scope, product, saved, token)

    colors = ((26, 85, 55), (225, 204, 156), (58, 95, 120))
    body, content_type = multipart(("product_id", product["id"]), *(
        ("images", png(color), f"frame-{index}.png", "image/png") for index, color in enumerate(colors)
    ))
    render = api(scope + "/renders", token=token, expected=201, payload=body, content_type=content_type)
    if render["status"] != "completed":
        raise RuntimeError(f"FFmpeg render {render['id']} failed in staging")
    video = fetch(WEB, "/api/v1" + scope + f"/renders/{render['id']}/video", token=token)
    assert b"ftyp" in video[:32]
    if release:
        body, content_type = multipart(("product_id", product["id"]), ("media", video, "clip.mp4", "video/mp4"))
        render = api(scope + "/renders", token=token, expected=201, payload=body, content_type=content_type)
        assert render["status"] == "completed", render
        video = fetch(WEB, "/api/v1" + scope + f"/renders/{render['id']}/video", token=token)
        verify_video(video)
    item = {"render_id": render["id"], "caption": "Staging smoke simulation", "include_comment": True,
            "scheduled_at": datetime.now(timezone.utc).isoformat()}
    api(scope + "/publishing/meta/publications", token=token, expected=403,
        payload={"render_id": render["id"], "caption": "Blocked live action"})
    api(scope + "/campaigns", token=token, expected=403,
        payload={"name": "Blocked live action", "mode": "live", "items": [item]})
    campaign = api(scope + "/campaigns", token=token, expected=201,
                   payload={"name": "Staging smoke", "items": [item]})
    api(scope + f"/campaigns/{campaign['id']}/actions", token=token, payload={"action": "activate"})

    def completed():
        queue = api(scope + "/campaigns", token=token)["campaigns"]
        job, = next(row["items"] for row in queue if row["id"] == campaign["id"])
        if job["state"] == "needs_attention":
            raise RuntimeError(f"Staging job failed: {job['error']}")
        return job["state"] == "completed"

    eventually(completed, "completed staging simulation")
    simulations = api(scope + "/publishing/simulations", token=token)
    assert any(row["render_id"] == render["id"] and row["comment_verified"] for row in simulations)
    verify_reports(scope, product, sub_id, token)
    eventually(lambda: metric_value('up{job="studio"}') == 1, "Prometheus scrape")
    eventually(lambda: metric_value("studio_worker_heartbeat_timestamp_seconds") > time.time() - 60,
               "fresh worker heartbeat")
    eventually(lambda: metric_value('studio_campaign_jobs{mode="simulation",state="completed"}') >= 1,
               "completed campaign metric")
    api("/auth/logout", token=token, payload={}, expected=204)
    print("Web/API, manual Affiliate link, storyboard, FFmpeg, queue, simulated comment, CSV and metrics passed.")
    if release:
        print("MP4 fixture import, stream metadata and full decode passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-metric", action="store_true")
    parser.add_argument("--release", action="store_true", help="Also import and decode a clip with FFmpeg available")
    options = parser.parse_args()
    if options.backup_metric:
        eventually(lambda: metric_value("studio_last_backup_timestamp_seconds") > time.time() - 180,
                   "fresh backup metric")
        print("Prometheus reported a successful recent backup.")
    else:
        run(release=options.release)
