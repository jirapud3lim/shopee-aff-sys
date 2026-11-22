"""Server-side transport for the connected Facebook Page."""

import hashlib
import hmac
import json
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from .config import Settings


class MetaError(Exception):
    """A sanitized provider error safe to show in Studio."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class MetaGraph:
    def __init__(self, settings: Settings):
        self.page_id = settings.meta_test_page_id
        self.version = settings.meta_graph_api_version
        self.token = settings.meta_page_access_token.get_secret_value()
        secret = settings.meta_app_secret.get_secret_value().encode()
        self.proof = hmac.new(secret, self.token.encode(), hashlib.sha256).hexdigest() if secret else ""
        context = ssl.create_default_context(cafile=settings.meta_ca_file or None)
        self.opener = build_opener(NoRedirect(), HTTPSHandler(context=context))

    def _send(self, request):
        try:
            with self.opener.open(request, timeout=25) as response:
                payload = json.load(response)
        except HTTPError as exc:
            try:
                code = json.load(exc).get("error", {}).get("code")
            except (ValueError, AttributeError):
                code = None
            raise MetaError(f"Meta API returned HTTP {exc.code} (code {code})" if isinstance(code, int)
                            else f"Meta API returned HTTP {exc.code}") from None
        except (URLError, OSError, ValueError):
            raise MetaError("Meta API did not return a readable response") from None
        if not isinstance(payload, dict) or "error" in payload:
            raise MetaError("Meta API returned an unexpected response")
        return payload

    def graph(self, edge, *, params=None, form=None):
        query = dict(params or {})
        if self.proof:
            query["appsecret_proof"] = self.proof
        url = f"https://graph.facebook.com/{self.version}/{edge}?{urlencode(query)}"
        headers = {"Authorization": f"Bearer {self.token}"}
        data = None
        if form is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urlencode(form).encode()
        return self._send(Request(url, data=data, headers=headers))

    def upload(self, url, video_id, video):
        endpoint = urlsplit(url)
        if (endpoint.scheme != "https" or endpoint.netloc != "rupload.facebook.com"
                or not re.fullmatch(r"/video-upload/(?:v[0-9]+\.[0-9]+/)?" + video_id, endpoint.path)):
            raise MetaError("Meta returned an unexpected upload URL")
        result = self._send(Request(url, data=video, headers={
            "Authorization": f"OAuth {self.token}", "offset": "0",
            "file_size": str(len(video)), "Content-Type": "application/octet-stream",
        }))
        if result.get("success") is not True:
            raise MetaError("Meta did not confirm the video upload")

    def reel(self, video_id):
        result = self.graph(video_id, params={"fields": "id,from,permalink_url,status"})
        if str(result.get("id")) != video_id or str(result.get("from", {}).get("id")) != self.page_id:
            raise MetaError("This Reel does not belong to the configured Facebook Page")
        return result

    def comments(self, video_id, pages=1):
        params = {
            "fields": "id,from,message,permalink_url,is_hidden",
            "limit": 50,
            "order": "reverse_chronological",
        }
        for _ in range(pages):
            page = self.graph(f"{video_id}/comments", params=params)
            for item in page.get("data", []):
                if str((item.get("from") or {}).get("id")) == self.page_id:
                    yield item
            paging = page.get("paging", {})
            cursor = paging.get("cursors", {}).get("after")
            if not paging.get("next") or not cursor or cursor == params.get("after"):
                break
            params["after"] = cursor
