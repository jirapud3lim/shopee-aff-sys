import json
from hashlib import sha256
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from app.catalog import shopee_affiliate as shopee
from app.core.config import Settings


@pytest.mark.parametrize("target, expected", [
    ("https://shopee.co.th/product/123/456?utm_content=facebook456----", "verified"),
    ("https://shopee.co.th/product/321/456", "mismatch"),
    ("https://shopee.co.th/product/123/456?utm_content=tiktok456", "mismatch"),
    ("https://example.com/product/123/456", "pending"),
    ("https://s.shopee.co.th@example.com/fixture", "pending"),
])
def test_link_destination_checks_each_redirect(monkeypatch, target, expected):
    start = "https://s.shopee.co.th/fixture"
    requests = []

    def redirect(request, _timeout):
        requests.append((request.full_url, request.get_method()))
        raise HTTPError(request.full_url, 302, "Moved", {"Location": target}, BytesIO())

    monkeypatch.setattr(shopee, "open_shopee", redirect)
    assert shopee.verify_destination(start, ("123", "456"), "facebook456") == expected
    assert requests == [(start, "HEAD")]


def test_link_destination_stops_after_four_redirect_requests(monkeypatch):
    requested = []

    def redirect(request, _timeout):
        requested.append(request.full_url)
        raise HTTPError(request.full_url, 302, "Moved", {"Location": "/fixture"}, BytesIO())

    monkeypatch.setattr(shopee, "open_shopee", redirect)
    assert shopee.verify_destination("https://s.shopee.co.th/fixture", ("123", "456"), "facebook456") == "pending"
    assert len(requested) == 4


@pytest.mark.parametrize("query, expected", [
    ("utm_source=an_123&utm_content=facebook456----", "verified"),
    ("utm_source=an_321&utm_content=facebook456----", "mismatch"),
    ("utm_source=an_123&utm_content=tiktok456----", "mismatch"),
    ("utm_source=an_123", "pending"),
    ("utm_content=facebook456----", "pending"),
])
def test_partner_wrapper_requires_matching_tracking_parameters(monkeypatch, query, expected):
    source = "https://shopee.co.th/product/123/456"
    link = shopee.partner_tracking_link(source, "123", "facebook456")
    assert parse_qs(urlsplit(link).query) == {
        "origin_link": [source], "affiliate_id": ["123"], "sub_id": ["facebook456----"],
    }

    def redirect(request, _timeout):
        assert request.full_url == link
        raise HTTPError(link, 302, "Moved", {"Location": f"{source}?{query}"}, BytesIO())

    monkeypatch.setattr(shopee, "open_shopee", redirect)
    assert shopee.verify_destination(link, ("123", "456"), "facebook456") == expected
    assert shopee.verify_destination(link, ("123", "999"), "facebook456") == "mismatch"
    assert shopee.verify_destination(link, ("123", "456"), "wrong") == "mismatch"


def test_shopee_signs_exact_body_and_rejects_untrusted_provider_result(monkeypatch):
    settings = Settings(shopee_affiliate_app_id="123", shopee_affiliate_secret="fixture-secret")
    monkeypatch.setattr(shopee.time, "time", lambda: 1700000000)
    source = "https://shopee.co.th/product/123/456"
    short_link = "https://s.shopee.co.th/fixture"

    def respond(request, _timeout):
        assert request.full_url == shopee.ENDPOINT
        assert json.loads(request.data)["variables"] == {"url": source, "tags": ["facebook456"]}
        signature = sha256(b"1231700000000" + request.data + b"fixture-secret").hexdigest()
        assert request.get_header("Authorization") == (
            f"SHA256 Credential=123, Timestamp=1700000000, Signature={signature}"
        )
        return BytesIO(json.dumps({"data": {"generateShortLink": {"shortLink": short_link}}}).encode())

    monkeypatch.setattr(shopee, "open_shopee", respond)
    assert shopee.generate_short_link(settings, source, "facebook456") == short_link
    short_link = "https://example.com/unsafe"
    with pytest.raises(shopee.ShopeeError):
        shopee.generate_short_link(settings, source, "facebook456")
