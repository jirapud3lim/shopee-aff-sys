"""Verify staging wiring through the web proxy without connecting external providers."""

import argparse
import json
import os
import secrets
import struct
import time
import zlib
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

WEB = "http://127.0.0.1:" + os.environ.get("STAGING_WEB_PORT", "3110")
PROM = "http://127.0.0.1:" + os.environ.get("STAGING_MONITOR_PORT", "19090")


def fetch(origin, path, *, token=None, payload=None, content_type="application/json", expected=200):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if payload is not None:
        headers["Content-Type"] = content_type
        if content_type == "application/json":
            payload = json.dumps(payload).encode()
    request = Request(origin + path, data=payload, headers=headers)
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


def png(color):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + bytes(color) * 8) * 8))
            + chunk(b"IEND", b""))


def multipart(product_id):
    boundary = secrets.token_hex(16)
    parts = [f'Content-Disposition: form-data; name="product_id"\r\n\r\n{product_id}'.encode()]
    colors = ((26, 85, 55), (225, 204, 156), (58, 95, 120))
    for index, color in enumerate(colors):
        parts.append(
            f'Content-Disposition: form-data; name="images"; filename="frame-{index}.png"\r\n'
            f"Content-Type: image/png\r\n\r\n".encode() + png(color)
        )
    delimiter = b"--" + boundary.encode()
    body = b"".join(delimiter + b"\r\n" + part + b"\r\n" for part in parts) + delimiter + b"--\r\n"
    return body, "multipart/form-data; boundary=" + boundary


def metric_value(query):
    response = fetch(PROM, "/api/v1/query?" + urlencode({"query": query}))
    values = json.loads(response)["data"]["result"]
    return float(values[0]["value"][1]) if values else 0


def run():
    assert api("/health") == {"status": "ok"}
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
        "name": "Staging smoke product", "source_url": "https://example.com/" + account,
        "affiliate_url": "https://example.com/affiliate", "image_rights_note": "Generated smoke-test fixtures",
    })
    body, content_type = multipart(product["id"])
    render = api(scope + "/renders", token=token, expected=201, payload=body, content_type=content_type)
    if render["status"] != "completed":
        raise RuntimeError(f"FFmpeg render {render['id']} failed in staging")
    video = fetch(WEB, "/api/v1" + scope + f"/renders/{render['id']}/video", token=token)
    assert b"ftyp" in video[:32]
    item = {"render_id": render["id"], "caption": "Staging smoke simulation",
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
    eventually(lambda: metric_value('up{job="studio"}') == 1, "Prometheus scrape")
    eventually(lambda: metric_value("studio_worker_heartbeat_timestamp_seconds") > time.time() - 60,
               "fresh worker heartbeat")
    eventually(lambda: metric_value('studio_campaign_jobs{mode="simulation",state="completed"}') >= 1,
               "completed campaign metric")
    api("/auth/logout", token=token, payload={}, expected=204)
    print("PostgreSQL, web proxy, FFmpeg, queue, simulated comment, live write guards and Prometheus passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-metric", action="store_true")
    if parser.parse_args().backup_metric:
        eventually(lambda: metric_value("studio_last_backup_timestamp_seconds") > time.time() - 180,
                   "fresh backup metric")
        print("Prometheus reported a successful recent backup.")
    else:
        run()
