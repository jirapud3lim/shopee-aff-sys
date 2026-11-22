from __future__ import annotations

import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from .redact import scrub_secrets

Transport = Callable[[str], tuple[int, str]]  # url -> (status, body)


class GraphError(Exception):
    pass


def appsecret_proof(access_token: str, app_secret: str) -> str:
    return hmac.new(app_secret.encode(), access_token.encode(), hashlib.sha256).hexdigest()


def urllib_transport(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except (urllib.error.URLError, TimeoutError) as e:
        raise GraphError(f"network error: {type(e).__name__}") from None


class GraphClient:
    def __init__(self, version: str, app_secret: str, transport: Transport = urllib_transport) -> None:
        self.version = version
        self._app_secret = app_secret
        self._transport = transport
        self.base = f"https://graph.facebook.com/{version}"

    def get(self, path_or_url: str, params: dict[str, str] | None = None, token: str | None = None) -> dict:
        params = dict(params or {})
        if token:
            params["access_token"] = token
            params["appsecret_proof"] = appsecret_proof(token, self._app_secret)
        if path_or_url.startswith("http"):
            url = path_or_url
            if token and "appsecret_proof=" not in url:
                url += ("&" if "?" in url else "?") + urllib.parse.urlencode(
                    {"appsecret_proof": params["appsecret_proof"]}
                )
        else:
            url = f"{self.base}/{path_or_url.lstrip('/')}?{urllib.parse.urlencode(params)}"
        status, body = self._transport(url)
        try:
            data = json.loads(body)
        except ValueError:
            raise GraphError(f"HTTP {status}: non-JSON response") from None
        if status >= 400 or "error" in data:
            err = data.get("error", {}) if isinstance(data, dict) else {}
            msg = scrub_secrets(str(err.get("message", "")), [token or "", self._app_secret])
            raise GraphError(
                f"Graph error error_code={err.get('code')} type={err.get('type')} "
                f"message={msg!r} fbtrace_id={err.get('fbtrace_id')} http={status}"
            )
        return data

    def exchange_code(self, client_id: str, redirect_uri: str, code: str) -> dict:
        return self.get(
            "oauth/access_token",
            {"client_id": client_id, "client_secret": self._app_secret, "redirect_uri": redirect_uri, "code": code},
        )

    def long_lived(self, client_id: str, short_token: str) -> dict:
        return self.get(
            "oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": client_id,
                "client_secret": self._app_secret,
                "fb_exchange_token": short_token,
            },
        )
