from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .domain import RemoteComment, RemoteReel, RemoteStatus


class AmbiguousOutcome(Exception):
    """Timeout / 5xx / network loss after the request may have been sent."""


class DefiniteFailure(Exception):
    """Provider rejected the request; no remote side effect."""


@dataclass(frozen=True)
class StartResult:
    video_id: str
    upload_url: str


class MetaReelsPort(Protocol):
    def start(self, page_id: str) -> StartResult: ...

    def upload(self, video_id: str, data: bytes) -> None: ...

    def finish(self, page_id: str, video_id: str, description: str) -> None: ...

    def get_status(self, video_id: str) -> RemoteStatus: ...

    def list_recent_reels(self, page_id: str, since: datetime) -> list[RemoteReel]: ...

    def post_comment(self, video_id: str, message: str) -> str: ...

    def list_comments(self, video_id: str) -> list[RemoteComment]: ...
