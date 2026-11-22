from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Callable

TTL_SECONDS = 600


class StateError(Exception):
    pass


class StateManager:
    def __init__(self, secret: str, clock: Callable[[], float] = time.time) -> None:
        self._key = secret.encode()
        self._clock = clock
        self._used: set[str] = set()

    def _sig(self, nonce: str, expiry: str) -> str:
        return hmac.new(self._key, f"{nonce}|{expiry}".encode(), hashlib.sha256).hexdigest()

    def issue(self) -> str:
        nonce = secrets.token_urlsafe(16)
        expiry = str(int(self._clock()) + TTL_SECONDS)
        return f"{nonce}.{expiry}.{self._sig(nonce, expiry)}"

    def verify(self, state: str | None) -> None:
        parts = (state or "").split(".")
        if len(parts) != 3:
            raise StateError("malformed state")
        nonce, expiry, sig = parts
        if not hmac.compare_digest(sig, self._sig(nonce, expiry)):
            raise StateError("bad state signature")
        if not expiry.isdigit() or int(expiry) < self._clock():
            raise StateError("state expired")
        if nonce in self._used:
            raise StateError("state already used")
        self._used.add(nonce)
