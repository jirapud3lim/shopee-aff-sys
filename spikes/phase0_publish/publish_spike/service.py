"""Orchestration of the publish job against a MetaReelsPort. In-memory repo for the spike."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from .domain import (
    Attempt,
    CommentStatus,
    InvalidTransition,
    Phase,
    PublishJob,
    ReconcileRequired,
    RemoteStatus,
    VideoPublishStatus as V,
    decide_comment_reconcile,
    decide_video_reconcile,
)
from .ports import AmbiguousOutcome, DefiniteFailure, MetaReelsPort

LIST_LOOKBACK = timedelta(hours=1)


class PublishService:
    def __init__(
        self,
        port: MetaReelsPort,
        now: Callable[[], datetime],
        settle_window: timedelta = timedelta(minutes=5),
    ) -> None:
        self._port = port
        self._now = now
        self._settle = settle_window
        self._jobs: dict[str, PublishJob] = {}

    def submit(self, idempotency_key: str, page_id: str, caption: str, affiliate_url: str) -> PublishJob:
        existing = self._jobs.get(idempotency_key)
        if existing is not None:
            return existing
        job = PublishJob(idempotency_key, page_id, caption, affiliate_url)
        self._jobs[idempotency_key] = job
        return job

    def adopt_persisted(self, job: PublishJob) -> None:
        self._jobs[job.idempotency_key] = job

    def _record(self, job: PublishJob, phase: Phase, outcome: str, detail: str = "") -> None:
        job.attempts.append(Attempt(phase, outcome, job.remote_video_id, detail))

    def _ambiguous(self, job: PublishJob, phase: Phase, exc: Exception) -> None:
        self._record(job, phase, "ambiguous", str(exc))
        job.ambiguous_phase = phase
        job.ambiguous_at = self._now()
        job.transition(V.UNKNOWN)

    def run(self, job: PublishJob, video_bytes: bytes = b"mp4") -> PublishJob:
        if job.status is V.UNKNOWN:
            raise ReconcileRequired("job is unknown; reconcile before any retry")
        if job.status is not V.QUEUED:
            return job  # idempotent: already running or terminal

        job.started_at = self._now()
        job.transition(V.STARTING)
        try:
            res = self._port.start(job.page_id)
        except AmbiguousOutcome as e:
            self._ambiguous(job, Phase.START, e)
            return job
        except DefiniteFailure as e:
            self._record(job, Phase.START, "definite_error", str(e))
            job.transition(V.FAILED)
            return job
        job.remote_video_id = res.video_id  # persisted before upload
        self._record(job, Phase.START, "ok")
        job.transition(V.UPLOADING)

        try:
            self._port.upload(res.video_id, video_bytes)
        except AmbiguousOutcome as e:
            self._ambiguous(job, Phase.UPLOAD, e)
            return job
        except DefiniteFailure as e:
            self._record(job, Phase.UPLOAD, "definite_error", str(e))
            job.transition(V.FAILED)
            return job
        self._record(job, Phase.UPLOAD, "ok")
        job.transition(V.FINISHING)

        try:
            self._port.finish(job.page_id, res.video_id, job.description)
        except AmbiguousOutcome as e:
            self._ambiguous(job, Phase.FINISH, e)
            return job
        except DefiniteFailure as e:
            self._record(job, Phase.FINISH, "definite_error", str(e))
            job.transition(V.FAILED)
            return job
        self._record(job, Phase.FINISH, "ok")
        job.transition(V.PROCESSING)
        return self.refresh(job)

    def refresh(self, job: PublishJob) -> PublishJob:
        """Poll status of a PROCESSING job."""
        if job.status is not V.PROCESSING or job.remote_video_id is None:
            return job
        try:
            st = self._port.get_status(job.remote_video_id)
        except (AmbiguousOutcome, DefiniteFailure):
            return job  # stay processing; polling is read-only and safe to repeat
        if st is RemoteStatus.PUBLISHED:
            job.transition(V.PUBLISHED)
        elif st is RemoteStatus.ERROR:
            job.transition(V.FAILED)
        return job

    def reconcile(self, job: PublishJob) -> PublishJob:
        if job.status is not V.UNKNOWN:
            raise InvalidTransition(f"reconcile only applies to unknown, got {job.status.value}")
        remote_status: RemoteStatus | None = None
        matches = []
        try:
            if job.remote_video_id is not None:
                remote_status = self._port.get_status(job.remote_video_id)
            else:
                since = (job.started_at or self._now()) - LIST_LOOKBACK
                reels = self._port.list_recent_reels(job.page_id, since)
                matches = [r for r in reels if job.marker in r.description]
        except (AmbiguousOutcome, DefiniteFailure):
            return job  # reconcile itself failed; remain unknown
        d = decide_video_reconcile(
            job,
            now=self._now(),
            settle_window=self._settle,
            remote_status=remote_status,
            marker_matches=matches,
        )
        if d.adopt_video_id is not None:
            job.remote_video_id = d.adopt_video_id
        if d.new_status is not V.UNKNOWN:
            self._record(job, Phase.STATUS, "ok", d.note)
            job.transition(d.new_status)
        return job

    def requeue(self, job: PublishJob) -> PublishJob:
        if job.status is V.UNKNOWN:
            raise ReconcileRequired("cannot requeue an unknown job without reconcile")
        job.transition(V.QUEUED)  # only valid from failed_safe_to_retry
        job.remote_video_id = None
        job.ambiguous_phase = None
        job.ambiguous_at = None
        return job

    def request_comment(self, job: PublishJob) -> PublishJob:
        if job.status is not V.PUBLISHED:
            raise InvalidTransition("comment requires a published video")
        if job.comment_status is CommentStatus.NOT_REQUESTED:
            job.comment_status = CommentStatus.PENDING
        return job

    def post_comment(self, job: PublishJob) -> PublishJob:
        if job.comment_status is CommentStatus.UNKNOWN:
            raise ReconcileRequired("comment is unknown; reconcile before retry")
        if job.comment_status not in (CommentStatus.PENDING, CommentStatus.FAILED):
            return job
        assert job.remote_video_id is not None
        job.comment_status = CommentStatus.POSTING
        try:
            job.comment_id = self._port.post_comment(job.remote_video_id, f"{job.affiliate_url}")
            job.comment_status = CommentStatus.POSTED
        except AmbiguousOutcome:
            job.comment_status = CommentStatus.UNKNOWN
            job.comment_ambiguous_at = self._now()
        except DefiniteFailure:
            job.comment_status = CommentStatus.FAILED
        return job

    def reconcile_comment(self, job: PublishJob) -> PublishJob:
        if job.comment_status is not CommentStatus.UNKNOWN:
            raise InvalidTransition("comment reconcile only applies to unknown")
        assert job.remote_video_id is not None
        try:
            comments = self._port.list_comments(job.remote_video_id)
        except (AmbiguousOutcome, DefiniteFailure):
            return job
        d = decide_comment_reconcile(
            job,
            page_id=job.page_id,
            comments=comments,
            now=self._now(),
            settle_window=self._settle,
        )
        job.comment_status = d.new_status
        if d.adopt_comment_id:
            job.comment_id = d.adopt_comment_id
        return job
