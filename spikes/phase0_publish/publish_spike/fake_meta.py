"""Scriptable in-memory double for the Meta Reels/comments API. Keeps remote state."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable

from .domain import Phase, RemoteComment, RemoteReel, RemoteStatus
from .ports import AmbiguousOutcome, DefiniteFailure, StartResult


class Behavior(str, Enum):
    OK = "ok"
    FAIL = "fail"  # definite rejection, no effect
    TIMEOUT_NO_EFFECT = "timeout_no_effect"  # ambiguous to caller; request never applied
    TIMEOUT_APPLIED = "timeout_applied"  # ambiguous to caller; effect applied remotely


@dataclass
class RemoteVideo:
    video_id: str
    page_id: str
    created_at: datetime
    status: RemoteStatus = RemoteStatus.UPLOADING
    description: str = ""


class FakeMetaReels:
    def __init__(self, now: Callable[[], datetime], page_author_id: str | None = None) -> None:
        self._now = now
        self._script: dict[Phase, deque[Behavior]] = defaultdict(deque)
        self._seq = 0
        self.videos: dict[str, RemoteVideo] = {}
        self.comments: dict[str, list[RemoteComment]] = defaultdict(list)
        self.hold_processing = False
        self.calls: list[Phase] = []
        self._page_author_id = page_author_id

    def script(self, phase: Phase, *behaviors: Behavior) -> None:
        self._script[phase].extend(behaviors)

    def complete_processing(self, video_id: str) -> None:
        self.videos[video_id].status = RemoteStatus.PUBLISHED

    def published_reels(self, page_id: str) -> list[RemoteVideo]:
        return [v for v in self.videos.values() if v.page_id == page_id and v.status is RemoteStatus.PUBLISHED]

    def _next(self, phase: Phase) -> Behavior:
        self.calls.append(phase)
        q = self._script[phase]
        return q.popleft() if q else Behavior.OK

    def _gate(self, phase: Phase, apply: Callable[[], object]) -> object:
        b = self._next(phase)
        if b is Behavior.FAIL:
            raise DefiniteFailure(f"{phase.value} rejected")
        if b is Behavior.TIMEOUT_NO_EFFECT:
            raise AmbiguousOutcome(f"{phase.value} timed out")
        result = apply()
        if b is Behavior.TIMEOUT_APPLIED:
            raise AmbiguousOutcome(f"{phase.value} timed out after apply")
        return result

    def start(self, page_id: str) -> StartResult:
        def apply() -> StartResult:
            self._seq += 1
            vid = f"v{self._seq}"
            self.videos[vid] = RemoteVideo(vid, page_id, self._now())
            return StartResult(vid, f"https://rupload.example/video-upload/{vid}")

        return self._gate(Phase.START, apply)  # type: ignore[return-value]

    def upload(self, video_id: str, data: bytes) -> None:
        def apply() -> None:
            self.videos[video_id].status = RemoteStatus.READY

        self._gate(Phase.UPLOAD, apply)

    def finish(self, page_id: str, video_id: str, description: str) -> None:
        def apply() -> None:
            v = self.videos[video_id]
            if v.status is not RemoteStatus.READY:
                raise DefiniteFailure("upload not complete")
            v.description = description
            v.status = RemoteStatus.PROCESSING if self.hold_processing else RemoteStatus.PUBLISHED

        self._gate(Phase.FINISH, apply)

    def get_status(self, video_id: str) -> RemoteStatus:
        def apply() -> RemoteStatus:
            v = self.videos.get(video_id)
            return v.status if v else RemoteStatus.NOT_FOUND

        return self._gate(Phase.STATUS, apply)  # type: ignore[return-value]

    def list_recent_reels(self, page_id: str, since: datetime) -> list[RemoteReel]:
        def apply() -> list[RemoteReel]:
            # Only reels that went through finish (carry a description) are listed.
            return [
                RemoteReel(v.video_id, v.description, v.created_at, v.status)
                for v in self.videos.values()
                if v.page_id == page_id
                and v.created_at >= since
                and v.status in (RemoteStatus.PROCESSING, RemoteStatus.PUBLISHED)
            ]

        return self._gate(Phase.LIST_REELS, apply)  # type: ignore[return-value]

    def post_comment(self, video_id: str, message: str) -> str:
        def apply() -> str:
            page_id = self._page_author_id or self.videos[video_id].page_id
            cid = f"c{sum(len(c) for c in self.comments.values()) + 1}"
            self.comments[video_id].append(RemoteComment(cid, message, page_id))
            return cid

        return self._gate(Phase.COMMENT, apply)  # type: ignore[return-value]

    def list_comments(self, video_id: str) -> list[RemoteComment]:
        return self._gate(Phase.LIST_COMMENTS, lambda: list(self.comments[video_id]))  # type: ignore[return-value]
