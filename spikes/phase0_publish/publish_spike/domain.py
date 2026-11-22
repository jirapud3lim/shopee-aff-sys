"""Pure domain logic for Reel publishing. No I/O, no clock reads, no provider calls."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class VideoPublishStatus(str, Enum):
    QUEUED = "queued"
    STARTING = "starting"
    UPLOADING = "uploading"
    FINISHING = "finishing"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    UNKNOWN = "unknown"
    FAILED_SAFE_TO_RETRY = "failed_safe_to_retry"


class CommentStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    POSTING = "posting"
    POSTED = "posted"
    FAILED = "failed"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"


class RemoteStatus(str, Enum):
    UPLOADING = "uploading"
    READY = "ready"  # upload complete, finish not applied
    PROCESSING = "processing"
    PUBLISHED = "published"
    ERROR = "error"
    NOT_FOUND = "not_found"


class Phase(str, Enum):
    START = "start"
    UPLOAD = "upload"
    FINISH = "finish"
    STATUS = "status"
    LIST_REELS = "list_reels"
    COMMENT = "comment"
    LIST_COMMENTS = "list_comments"


class InvalidTransition(Exception):
    pass


class ReconcileRequired(Exception):
    """Raised when a job in `unknown` is asked to run/retry without reconciliation."""


V = VideoPublishStatus

ALLOWED_TRANSITIONS: dict[V, frozenset[V]] = {
    V.QUEUED: frozenset({V.STARTING}),
    V.STARTING: frozenset({V.UPLOADING, V.FAILED, V.UNKNOWN}),
    V.UPLOADING: frozenset({V.FINISHING, V.FAILED, V.UNKNOWN}),
    V.FINISHING: frozenset({V.PROCESSING, V.PUBLISHED, V.FAILED, V.UNKNOWN}),
    V.PROCESSING: frozenset({V.PUBLISHED, V.FAILED, V.UNKNOWN}),
    V.UNKNOWN: frozenset({V.PROCESSING, V.PUBLISHED, V.FAILED, V.FAILED_SAFE_TO_RETRY}),
    V.FAILED: frozenset(),
    V.FAILED_SAFE_TO_RETRY: frozenset({V.QUEUED}),
    V.PUBLISHED: frozenset(),
}


def make_idempotency_key(org_id: str, campaign_item_id: str, page_id: str, video_asset_id: str) -> str:
    raw = "\x1f".join((org_id, campaign_item_id, page_id, video_asset_id))
    return hashlib.sha256(raw.encode()).hexdigest()


def marker_for(idempotency_key: str) -> str:
    return f"#af{idempotency_key[:10]}"


@dataclass(frozen=True)
class RemoteReel:
    video_id: str
    description: str
    created_at: datetime
    status: RemoteStatus


@dataclass(frozen=True)
class RemoteComment:
    comment_id: str
    message: str
    author_id: str


@dataclass(frozen=True)
class Attempt:
    phase: Phase
    outcome: str  # ok | definite_error | ambiguous
    remote_video_id: str | None = None
    detail: str = ""


@dataclass
class PublishJob:
    idempotency_key: str
    page_id: str
    caption: str
    affiliate_url: str
    status: V = V.QUEUED
    remote_video_id: str | None = None
    ambiguous_phase: Phase | None = None
    ambiguous_at: datetime | None = None
    started_at: datetime | None = None
    attempts: list[Attempt] = field(default_factory=list)
    comment_status: CommentStatus = CommentStatus.NOT_REQUESTED
    comment_id: str | None = None
    comment_ambiguous_at: datetime | None = None

    @property
    def marker(self) -> str:
        return marker_for(self.idempotency_key)

    @property
    def description(self) -> str:
        return f"{self.caption}\n{self.marker}"

    def transition(self, new: V) -> None:
        if new not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidTransition(f"{self.status.value} -> {new.value}")
        self.status = new


@dataclass(frozen=True)
class VideoReconcileDecision:
    new_status: V
    adopt_video_id: str | None = None
    note: str = ""


def decide_video_reconcile(
    job: PublishJob,
    *,
    now: datetime,
    settle_window: timedelta,
    remote_status: RemoteStatus | None,
    marker_matches: list[RemoteReel],
) -> VideoReconcileDecision:
    """Decide the outcome of an `unknown` job from observed remote state.

    `remote_status` is set when the job has a persisted remote video id.
    `marker_matches` is the Page's recent reels whose description carries the job marker
    (used only when the video id was never persisted).
    """
    waited = job.ambiguous_at is not None and now - job.ambiguous_at >= settle_window

    if job.remote_video_id is not None:
        if remote_status is RemoteStatus.PUBLISHED:
            return VideoReconcileDecision(V.PUBLISHED, note="remote published")
        if remote_status is RemoteStatus.PROCESSING:
            return VideoReconcileDecision(V.PROCESSING, note="remote processing")
        if remote_status is RemoteStatus.ERROR:
            return VideoReconcileDecision(V.FAILED_SAFE_TO_RETRY, note="remote error, not published")
        if remote_status in (RemoteStatus.UPLOADING, RemoteStatus.READY, RemoteStatus.NOT_FOUND):
            if waited:
                return VideoReconcileDecision(V.FAILED_SAFE_TO_RETRY, note="not published after settle window")
            return VideoReconcileDecision(V.UNKNOWN, note="not published yet, inside settle window")
        return VideoReconcileDecision(V.UNKNOWN, note="no remote status observed")

    if marker_matches:
        newest = max(marker_matches, key=lambda r: r.created_at)
        if newest.status is RemoteStatus.PUBLISHED:
            return VideoReconcileDecision(V.PUBLISHED, adopt_video_id=newest.video_id, note="adopted by marker")
        if newest.status is RemoteStatus.PROCESSING:
            return VideoReconcileDecision(V.PROCESSING, adopt_video_id=newest.video_id, note="adopted by marker")
        return VideoReconcileDecision(V.UNKNOWN, adopt_video_id=newest.video_id, note="marker match not published")
    if waited:
        return VideoReconcileDecision(V.FAILED_SAFE_TO_RETRY, note="no remote reel with marker after window")
    return VideoReconcileDecision(V.UNKNOWN, note="no marker match yet, inside settle window")


@dataclass(frozen=True)
class CommentReconcileDecision:
    new_status: CommentStatus
    adopt_comment_id: str | None = None


def decide_comment_reconcile(
    job: PublishJob,
    *,
    page_id: str,
    comments: list[RemoteComment],
    now: datetime,
    settle_window: timedelta,
) -> CommentReconcileDecision:
    for c in comments:
        if c.author_id == page_id and job.affiliate_url in c.message:
            return CommentReconcileDecision(CommentStatus.POSTED, adopt_comment_id=c.comment_id)
    waited = job.comment_ambiguous_at is not None and now - job.comment_ambiguous_at >= settle_window
    if waited:
        return CommentReconcileDecision(CommentStatus.FAILED)
    return CommentReconcileDecision(CommentStatus.UNKNOWN)
