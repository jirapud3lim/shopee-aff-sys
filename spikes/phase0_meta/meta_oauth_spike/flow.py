from __future__ import annotations

import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from cryptography.fernet import Fernet

from .config import Config
from .graph import GraphClient, GraphError
from .redact import scrub_secrets
from .state import StateError, StateManager


def authorize_url(cfg: Config, state: str) -> str:
    q = {"client_id": cfg.app_id, "redirect_uri": cfg.redirect_uri, "state": state, "response_type": "code"}
    if cfg.config_id:
        q["config_id"] = cfg.config_id
    else:
        q["scope"] = cfg.scopes
    return f"https://www.facebook.com/{cfg.version}/dialog/oauth?{urllib.parse.urlencode(q)}"


def fetch_pages(graph: GraphClient, token: str) -> dict[str, dict]:
    pages: dict[str, dict] = {}
    nxt: str | None = "me/accounts"
    params: dict[str, str] | None = {"fields": "id,name,tasks,access_token"}
    while nxt:
        data = graph.get(nxt, params, token)
        for p in data.get("data", []):
            pages[p["id"]] = {"name": p.get("name"), "tasks": p.get("tasks", []), "page_token": p.get("access_token")}
        nxt = data.get("paging", {}).get("next")
        params = None
    return pages


def write_private(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.chmod(path, 0o600)


class OAuthFlow:
    def __init__(
        self,
        cfg: Config,
        graph: GraphClient,
        state: StateManager,
        out_dir: Path,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.cfg, self.graph, self.state, self.out_dir, self._now = cfg, graph, state, out_dir, now

    @property
    def token_file(self) -> Path:
        return self.out_dir / ".secrets" / "meta_tokens.enc"

    def start_url(self) -> str:
        return authorize_url(self.cfg, self.state.issue())

    def handle_callback(self, params: dict[str, str]) -> tuple[int, dict]:
        """Returns (http_status, summary_or_error). Never contains tokens."""
        try:
            self.state.verify(params.get("state"))
        except StateError as e:
            return 400, {"error": f"invalid state: {e}"}
        if "error" in params:
            return 400, {
                "error": "Meta returned an error",
                "meta_error": scrub_secrets(params.get("error", ""), self.cfg.secret_values())[:100],
                "meta_error_reason": scrub_secrets(params.get("error_reason", ""), self.cfg.secret_values())[:100],
                "meta_error_description": scrub_secrets(params.get("error_description", ""), self.cfg.secret_values())[:300],
            }
        code = params.get("code")
        if not code:
            return 400, {"error": "missing code"}
        try:
            short = self.graph.exchange_code(self.cfg.app_id, self.cfg.redirect_uri, code)
            long = self.graph.long_lived(self.cfg.app_id, short["access_token"])
            token = long["access_token"]
            expires_in = long.get("expires_in")
            me = self.graph.get("me", {"fields": "id,name"}, token)
            perms = self.graph.get("me/permissions", None, token).get("data", [])
            pages = fetch_pages(self.graph, token)
        except (GraphError, KeyError) as e:
            return 502, {"error": scrub_secrets(f"{type(e).__name__}: {e}", self.cfg.secret_values() + [code])}

        granted = sorted(p["permission"] for p in perms if p.get("status") == "granted")
        declined = sorted(p["permission"] for p in perms if p.get("status") == "declined")
        now = self._now()
        expires_at = (
            datetime.fromtimestamp(now.timestamp() + int(expires_in), timezone.utc).isoformat() if expires_in else None
        )
        payload = {
            "user_token": token,
            "expires_at": expires_at,
            "granted_scopes": granted,
            "declined_scopes": declined,
            "pages": pages,
        }
        write_private(self.token_file, Fernet(self.cfg.encryption_key.encode()).encrypt(json.dumps(payload).encode()))

        summary = {
            "timestamp": now.isoformat(),
            "api_version": self.cfg.version,
            "login_mode": "config_id" if self.cfg.config_id else "scope",
            "granted_permissions": granted,
            "declined_permissions": declined,
            "token_expires_at": expires_at,
            "pages": [{"id": pid, "name": p["name"], "tasks": p["tasks"]} for pid, p in pages.items()],
        }
        ev = self.out_dir / "evidence" / f"oauth_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
        ev.parent.mkdir(parents=True, exist_ok=True)
        ev.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        return 200, summary


def check_tokens(cfg: Config, out_dir: Path) -> dict:
    raw = (out_dir / ".secrets" / "meta_tokens.enc").read_bytes()
    d = json.loads(Fernet(cfg.encryption_key.encode()).decrypt(raw))
    return {
        "expires_at": d["expires_at"],
        "has_user_token": bool(d.get("user_token")),
        "granted_scopes": d["granted_scopes"],
        "pages": [
            {"id": pid, "name": p["name"], "tasks": p["tasks"], "has_page_token": bool(p.get("page_token"))}
            for pid, p in d["pages"].items()
        ],
    }
