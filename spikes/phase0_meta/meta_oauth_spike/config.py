from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k.strip()] = v
    return out


@dataclass(frozen=True)
class Config:
    app_id: str
    app_secret: str = field(repr=False)
    version: str
    redirect_uri: str
    scopes: str
    encryption_key: str = field(repr=False)
    state_secret: str = field(repr=False)
    config_id: str = ""

    @property
    def callback_path(self) -> str:
        return urlparse(self.redirect_uri).path

    def secret_values(self) -> list[str]:
        return [self.app_secret, self.encryption_key, self.state_secret]

    @classmethod
    def from_env_file(cls, path: Path) -> "Config":
        e = {**load_env(path), **{k: v for k, v in os.environ.items() if k.startswith(("META_", "TOKEN_", "OAUTH_"))}}
        missing = [k for k in ("META_APP_ID", "META_APP_SECRET", "META_OAUTH_REDIRECT_URI", "TOKEN_ENCRYPTION_KEY", "OAUTH_STATE_SECRET") if not e.get(k)]
        if missing:
            raise SystemExit(f"missing required env keys: {', '.join(missing)}")
        return cls(
            app_id=e["META_APP_ID"],
            app_secret=e["META_APP_SECRET"],
            version=e.get("META_GRAPH_API_VERSION") or "v27.0",
            redirect_uri=e["META_OAUTH_REDIRECT_URI"],
            scopes=e.get("META_OAUTH_SCOPES", ""),
            encryption_key=e["TOKEN_ENCRYPTION_KEY"],
            state_secret=e["OAUTH_STATE_SECRET"],
            config_id=e.get("META_LOGIN_CONFIG_ID", ""),
        )
