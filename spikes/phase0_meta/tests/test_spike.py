from __future__ import annotations

import json
import stat
import urllib.parse
from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet

from meta_oauth_spike.config import Config
from meta_oauth_spike.flow import OAuthFlow, authorize_url, check_tokens
from meta_oauth_spike.graph import GraphClient, appsecret_proof
from meta_oauth_spike.redact import redact
from meta_oauth_spike.state import StateError, StateManager

APP_SECRET = "FAKE_APP_SECRET_xyz"
CODE = "FAKE_CODE_123"
SHORT = "FAKE_SHORT_TOKEN"
LONG = "FAKE_LONG_TOKEN"
PAGE_TOKEN = "FAKE_PAGE_TOKEN"
STATE_SECRET = "FAKE_STATE_SECRET"
KEY = Fernet.generate_key().decode()
FAKES = [APP_SECRET, CODE, SHORT, LONG, PAGE_TOKEN, STATE_SECRET, KEY]


def make_cfg(**kw) -> Config:
    base = dict(
        app_id="1234567890",
        app_secret=APP_SECRET,
        version="v27.0",
        redirect_uri="http://localhost:8000/api/v1/connections/meta/callback",
        scopes="pages_show_list,pages_manage_posts",
        encryption_key=KEY,
        state_secret=STATE_SECRET,
    )
    base.update(kw)
    return Config(**base)


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


# ---- state
def test_state_valid_accepted():
    m = StateManager("s", Clock())
    m.verify(m.issue())


def test_state_tampered_rejected():
    m = StateManager("s", Clock())
    n, e, s = m.issue().split(".")
    with pytest.raises(StateError):
        m.verify(f"{n}.{int(e) + 1}.{s}")
    with pytest.raises(StateError):
        m.verify(f"{n}.{e}.{'0' * len(s)}")
    with pytest.raises(StateError):
        m.verify(None)


def test_state_expired_rejected():
    c = Clock()
    m = StateManager("s", c)
    st = m.issue()
    c.t += 601
    with pytest.raises(StateError):
        m.verify(st)


def test_state_reuse_rejected():
    m = StateManager("s", Clock())
    st = m.issue()
    m.verify(st)
    with pytest.raises(StateError):
        m.verify(st)


# ---- redaction
@pytest.mark.parametrize("k", ["access_token", "client_secret", "code", "appsecret_proof", "fb_exchange_token"])
def test_redact_url_and_json(k):
    url = f"https://graph.facebook.com/v27.0/x?a=1&{k}=SENSITIVEVAL&b=2"
    out = redact(url)
    assert "SENSITIVEVAL" not in out and "a=1" in out and "b=2" in out
    body = json.dumps({k: "SENSITIVEVAL", "keep": "ok"})
    out = redact(body)
    assert "SENSITIVEVAL" not in out and "ok" in out
    nested = json.dumps({"message": json.dumps({k: "SENSITIVEVAL"})})
    assert "SENSITIVEVAL" not in redact(nested)


def test_appsecret_proof_known_vector():
    # HMAC-SHA256(key="key", msg="The quick brown fox jumps over the lazy dog")
    assert (
        appsecret_proof("The quick brown fox jumps over the lazy dog", "key")
        == "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"
    )


# ---- authorize url
def test_authorize_url_scope_and_config_id():
    q = urllib.parse.parse_qs(urllib.parse.urlparse(authorize_url(make_cfg(), "st")).query)
    assert q["scope"] == ["pages_show_list,pages_manage_posts"] and "config_id" not in q
    assert q["response_type"] == ["code"] and q["state"] == ["st"]
    u = authorize_url(make_cfg(config_id="CFG1"), "st")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
    assert q["config_id"] == ["CFG1"] and "scope" not in q
    assert u.startswith("https://www.facebook.com/v27.0/dialog/oauth?")


# ---- callback flow
class FakeTransport:
    def __init__(self):
        self.urls: list[str] = []

    def __call__(self, url: str):
        self.urls.append(url)
        u = urllib.parse.urlparse(url)
        q = urllib.parse.parse_qs(u.query)
        if u.path.endswith("/oauth/access_token"):
            if "code" in q:
                assert q["code"] == [CODE]
                return 200, json.dumps({"access_token": SHORT, "token_type": "bearer"})
            assert q["fb_exchange_token"] == [SHORT]
            return 200, json.dumps({"access_token": LONG, "expires_in": 5183944})
        assert q["access_token"] == [LONG]
        assert q["appsecret_proof"] == [appsecret_proof(LONG, APP_SECRET)]
        if u.path.endswith("/me"):
            return 200, json.dumps({"id": "u1", "name": "Test User"})
        if u.path.endswith("/me/permissions"):
            return 200, json.dumps(
                {
                    "data": [
                        {"permission": "pages_show_list", "status": "granted"},
                        {"permission": "pages_manage_posts", "status": "declined"},
                    ]
                }
            )
        if u.path.endswith("/me/accounts"):
            return 200, json.dumps(
                {
                    "data": [{"id": "p1", "name": "Page One", "tasks": ["CREATE_CONTENT"], "access_token": PAGE_TOKEN}],
                    "paging": {"next": "https://graph.facebook.com/v27.0/me/accounts?after=X&access_token=" + LONG},
                }
            )
        if u.path.endswith("/me/accounts") or "after=X" in url:
            return 200, json.dumps({"data": []})
        raise AssertionError(url)


def make_flow(tmp_path, transport):
    cfg = make_cfg()
    c = Clock()
    flow = OAuthFlow(
        cfg,
        GraphClient(cfg.version, cfg.app_secret, transport),
        StateManager(STATE_SECRET, c),
        tmp_path,
        now=lambda: datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc),
    )
    return flow, cfg


def test_callback_happy_path(tmp_path, capsys):
    t = FakeTransport()
    # second page of accounts: distinguish by 'after=X'
    orig = t.__call__

    def transport(url):
        if "after=X" in url and "/me/accounts" in url:
            t.urls.append(url)
            return 200, json.dumps({"data": [{"id": "p2", "name": "Page Two", "tasks": [], "access_token": "FAKE_PAGE_TOKEN"}]})
        return orig(url)

    flow, cfg = make_flow(tmp_path, transport)
    st = flow.state.issue()
    status, summary = flow.handle_callback({"code": CODE, "state": st})
    print(json.dumps(summary))
    assert status == 200
    assert [p["id"] for p in summary["pages"]] == ["p1", "p2"]
    assert summary["granted_permissions"] == ["pages_show_list"]
    assert summary["declined_permissions"] == ["pages_manage_posts"]

    enc = tmp_path / ".secrets" / "meta_tokens.enc"
    assert stat.S_IMODE(enc.stat().st_mode) == 0o600
    assert stat.S_IMODE(enc.parent.stat().st_mode) == 0o700
    raw = enc.read_bytes()
    assert LONG.encode() not in raw
    d = json.loads(Fernet(KEY.encode()).decrypt(raw))
    assert d["user_token"] == LONG and d["pages"]["p1"]["page_token"] == PAGE_TOKEN

    checked = check_tokens(cfg, tmp_path)
    assert checked["pages"][0] == {"id": "p1", "name": "Page One", "tasks": ["CREATE_CONTENT"], "has_page_token": True}
    assert not any(f in json.dumps(checked) for f in FAKES)

    files = list((tmp_path / "evidence").glob("oauth_*.json"))
    assert len(files) == 1
    text = files[0].read_text()
    out = capsys.readouterr().out
    for f in FAKES:
        assert f not in text and f not in out and f not in st


def test_callback_meta_error_makes_no_calls(tmp_path):
    t = FakeTransport()
    flow, _ = make_flow(tmp_path, t)
    st = flow.state.issue()
    status, data = flow.handle_callback(
        {"error": "access_denied", "error_reason": "user_denied", "error_description": "Permissions error.", "state": st}
    )
    assert status == 400 and data["meta_error"] == "access_denied"
    assert t.urls == []
    assert not (tmp_path / ".secrets").exists()


def test_callback_bad_state_makes_no_calls(tmp_path):
    t = FakeTransport()
    flow, _ = make_flow(tmp_path, t)
    status, _ = flow.handle_callback({"code": CODE, "state": "bad.state.sig"})
    assert status == 400 and t.urls == []
    st = flow.state.issue()
    flow.state.verify(st)
    status, _ = flow.handle_callback({"code": CODE, "state": st})
    assert status == 400 and t.urls == []


def test_graph_error_surfaces_only_safe_fields(tmp_path):
    def transport(url):
        return 400, json.dumps(
            {"error": {"message": f"bad access_token={LONG} here", "type": "OAuthException", "code": 190, "fbtrace_id": "T1"}}
        )

    flow, _ = make_flow(tmp_path, transport)
    status, data = flow.handle_callback({"code": CODE, "state": flow.state.issue()})
    assert status == 502
    s = json.dumps(data)
    assert "error_code=190" in s and "T1" in s and LONG not in s and CODE not in s
