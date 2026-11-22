from __future__ import annotations

import re

SENSITIVE = ("access_token", "client_secret", "code", "appsecret_proof", "fb_exchange_token")

_param = re.compile(r"(?P<k>\b(?:%s))=(?P<v>[^&\s\"']*)" % "|".join(SENSITIVE))
_json = re.compile(r"(?P<q>\\?\")(?P<k>%s)(?P=q)\s*:\s*(?P<vq>\\?\")(?:[^\"\\]|\\.)*?(?P=vq)" % "|".join(SENSITIVE))


def redact(text: str) -> str:
    text = _param.sub(lambda m: f"{m['k']}=<redacted>", text)
    return _json.sub(lambda m: f"{m['q']}{m['k']}{m['q']}: {m['vq']}<redacted>{m['vq']}", text)


def scrub_secrets(text: str, secrets: list[str]) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "<redacted>")
    return redact(text)
