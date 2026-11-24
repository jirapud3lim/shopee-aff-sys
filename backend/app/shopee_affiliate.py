"""Thai Shopee Affiliate Open API and bounded link destination checks."""

import json
import re
import time
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .config import Settings

ENDPOINT = "https://open-api.affiliate.shopee.co.th/graphql"
LISTING_HOSTS = {"shopee.co.th", "www.shopee.co.th"}
SHORT_HOST = "s.shopee.co.th"
PARTNER_REDIRECT_PATH = "/an_redir"
LISTING_PATH = re.compile(r"/(?:product|opaanlp)/([0-9]{1,20})/([0-9]{1,20})/?|/[^/]+-i\.([0-9]{1,20})\.([0-9]{1,20})/?")


class ShopeeError(Exception):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        return None


def open_shopee(request, timeout):
    return build_opener(ProxyHandler({}), NoRedirects()).open(request, timeout=timeout)


def allowed_url(url):
    if not url or any(ord(char) <= 32 or ord(char) == 127 for char in url) or "\\" in url:
        return None
    try:
        parts = urlsplit(url)
        if parts.scheme == "https" and parts.netloc.lower() in LISTING_HOSTS | {SHORT_HOST}:
            return parts
    except ValueError:
        pass
    return None


def listing_identity(url):
    parts = allowed_url(url)
    if parts is None or parts.hostname not in LISTING_HOSTS:
        return None
    match = LISTING_PATH.fullmatch(parts.path)
    if match:
        return tuple(value for value in match.groups() if value is not None)
    return None


def partner_tracking_link(source_url: str, affiliate_id: str, sub_id: str) -> str:
    """Build the documented Shopee partner wrapper without a provider request."""
    query = urlencode({"origin_link": source_url, "affiliate_id": affiliate_id, "sub_id": sub_id + "----"})
    return f"https://{SHORT_HOST}{PARTNER_REDIRECT_PATH}?{query}"


def verify_destination(url, expected, sub_id):
    initial = allowed_url(url)
    partner_id = None
    if initial and initial.hostname == SHORT_HOST and initial.path == PARTNER_REDIRECT_PATH:
        params = parse_qs(initial.query)
        publisher = params.get("affiliate_id", [])
        origin = params.get("origin_link", [])
        tags = params.get("sub_id", [])
        if (len(publisher) != 1 or not re.fullmatch(r"[0-9]{1,32}", publisher[0])
                or len(origin) != 1 or listing_identity(origin[0]) != expected
                or (sub_id and (len(tags) != 1 or tags[0].split("-")[0] != sub_id))):
            return "mismatch"
        partner_id = publisher[0]

    deadline = time.monotonic() + 4
    for _ in range(4):
        parts = allowed_url(url)
        if parts is None:
            return "pending"
        identity = listing_identity(url)
        if identity is not None:
            params = parse_qs(parts.query)
            tag = params.get("utm_content", [])
            if identity != expected or (sub_id and tag and (len(tag) != 1 or sub_id not in tag[0].split("-"))):
                return "mismatch"
            if partner_id is not None:
                publisher = params.get("utm_source")
                if publisher and publisher != [f"an_{partner_id}"]:
                    return "mismatch"
                if not publisher or (sub_id and not tag):
                    return "pending"
            return "verified"
        if parts.hostname != SHORT_HOST or not parts.path.startswith("/") or parts.path == "/":
            return "pending"
        timeout = deadline - time.monotonic()
        if timeout <= 0:
            return "pending"
        try:
            with open_shopee(Request(url, method="HEAD"), timeout):
                return "pending"
        except HTTPError as exc:
            with exc:
                location = exc.headers.get("Location")
                if exc.code not in (301, 302, 303, 307, 308) or not location:
                    return "pending"
                try:
                    url = urljoin(url, location)
                except ValueError:
                    return "pending"
        except (URLError, OSError, ValueError):
            return "pending"
    return "pending"


def generate_short_link(settings: Settings, source_url: str, sub_id: str) -> str:
    query = (
        "mutation GenerateShortLink($url: String!, $tags: [String!]) { "
        "generateShortLink(input: {originUrl: $url, subIds: $tags}) { shortLink } }"
    )
    payload = json.dumps({"query": query, "variables": {"url": source_url, "tags": [sub_id]}},
                         separators=(",", ":")).encode()
    app_id = settings.shopee_affiliate_app_id
    timestamp = str(int(time.time()))
    signature = sha256((app_id + timestamp).encode() + payload
                       + settings.shopee_affiliate_secret.get_secret_value().encode()).hexdigest()
    request = Request(ENDPOINT, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}",
    })
    try:
        with open_shopee(request, 10) as response:
            body = json.loads(response.read(64 * 1024))
        if body.get("errors"):
            raise ValueError
        url = body["data"]["generateShortLink"]["shortLink"]
        parts = allowed_url(url) if isinstance(url, str) and len(url) <= 2083 else None
        if parts is None or parts.hostname != SHORT_HOST or not parts.path or parts.path == "/":
            raise ValueError
        return url
    except HTTPError as exc:
        exc.close()
        raise ShopeeError("Shopee Open API rejected the request") from exc
    except (URLError, OSError, ValueError, KeyError, AttributeError, TypeError) as exc:
        raise ShopeeError("Shopee Open API could not generate a link") from exc
