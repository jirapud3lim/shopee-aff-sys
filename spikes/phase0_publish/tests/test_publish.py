from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from publish_spike.domain import (
    CommentStatus,
    InvalidTransition,
    Phase,
    ReconcileRequired,
    VideoPublishStatus as V,
    make_idempotency_key,
)
from publish_spike.fake_meta import Behavior as B, FakeMetaReels
from publish_spike.service import PublishService

PAGE = "page-1"
URL = "https://shope.ee/abc123"


class Clock:
    def __init__(self) -> None:
        self.t = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kw: float) -> None:
        self.t += timedelta(**kw)


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def fake(clock: Clock) -> FakeMetaReels:
    return FakeMetaReels(clock)


@pytest.fixture
def svc(fake: FakeMetaReels, clock: Clock) -> PublishService:
    return PublishService(fake, clock, settle_window=timedelta(minutes=5))


def key(item: str = "item-1") -> str:
    return make_idempotency_key("org-1", item, PAGE, "asset-1")


def submit(svc: PublishService, item: str = "item-1"):
    return svc.submit(key(item), PAGE, "Great product", URL)


def test_happy_path(svc, fake):
    job = svc.run(submit(svc))
    assert job.status is V.PUBLISHED
    assert job.remote_video_id == "v1"
    assert len(fake.published_reels(PAGE)) == 1
    assert fake.videos["v1"].description.endswith(job.marker)
    assert [a.phase for a in job.attempts] == [Phase.START, Phase.UPLOAD, Phase.FINISH]


def test_processing_then_refresh_publishes(svc, fake):
    fake.hold_processing = True
    job = svc.run(submit(svc))
    assert job.status is V.PROCESSING
    fake.complete_processing(job.remote_video_id)
    assert svc.refresh(job).status is V.PUBLISHED


def test_video_id_persisted_before_upload(svc, fake):
    fake.script(Phase.UPLOAD, B.TIMEOUT_NO_EFFECT)
    job = svc.run(submit(svc))
    assert job.status is V.UNKNOWN
    assert job.remote_video_id == "v1"


def test_finish_timeout_but_remote_published_reconciles_without_duplicate(svc, fake):
    fake.script(Phase.FINISH, B.TIMEOUT_APPLIED)
    job = svc.run(submit(svc))
    assert job.status is V.UNKNOWN
    svc.reconcile(job)
    assert job.status is V.PUBLISHED
    assert len(fake.published_reels(PAGE)) == 1


def test_finish_timeout_not_applied_stays_unknown_then_safe_to_retry(svc, fake, clock):
    fake.script(Phase.FINISH, B.TIMEOUT_NO_EFFECT)
    job = svc.run(submit(svc))
    svc.reconcile(job)
    assert job.status is V.UNKNOWN  # inside settle window: finish might still land
    clock.advance(minutes=6)
    svc.reconcile(job)
    assert job.status is V.FAILED_SAFE_TO_RETRY
    svc.requeue(job)
    svc.run(job)
    assert job.status is V.PUBLISHED
    assert len(fake.published_reels(PAGE)) == 1
    assert job.attempts[-1].remote_video_id == "v2"


def test_start_timeout_adopts_reel_found_by_marker(fake, clock):
    # A lost worker finished a reel (carrying the marker) but its state was never persisted.
    lost = PublishService(fake, clock)
    done = lost.run(lost.submit(key(), PAGE, "Great product", URL))
    assert done.status is V.PUBLISHED

    svc = PublishService(fake, clock)
    fake.script(Phase.START, B.TIMEOUT_NO_EFFECT)
    job = svc.submit(key(), PAGE, "Great product", URL)
    svc.run(job)
    assert job.status is V.UNKNOWN and job.remote_video_id is None
    svc.reconcile(job)
    assert job.status is V.PUBLISHED
    assert job.remote_video_id == done.remote_video_id
    assert len(fake.published_reels(PAGE)) == 1


def test_start_timeout_nothing_published_becomes_failed_safe_to_retry(svc, fake, clock):
    fake.script(Phase.START, B.TIMEOUT_APPLIED)  # orphan upload session, no id, never finished
    job = svc.run(submit(svc))
    assert job.status is V.UNKNOWN and job.remote_video_id is None
    svc.reconcile(job)
    assert job.status is V.UNKNOWN  # window not elapsed
    clock.advance(minutes=6)
    svc.reconcile(job)
    assert job.status is V.FAILED_SAFE_TO_RETRY
    assert fake.published_reels(PAGE) == []
    svc.requeue(job)
    svc.run(job)
    assert job.status is V.PUBLISHED
    assert len(fake.published_reels(PAGE)) == 1


def test_retry_of_unknown_without_reconcile_is_rejected(svc, fake):
    fake.script(Phase.FINISH, B.TIMEOUT_APPLIED)
    job = svc.run(submit(svc))
    calls_before = list(fake.calls)
    with pytest.raises(ReconcileRequired):
        svc.run(job)
    with pytest.raises(ReconcileRequired):
        svc.requeue(job)
    assert fake.calls == calls_before


def test_invalid_transition_rejected():
    from publish_spike.domain import PublishJob

    job = PublishJob(key(), PAGE, "c", URL)
    with pytest.raises(InvalidTransition):
        job.transition(V.PUBLISHED)


def test_same_idempotency_key_twice_creates_one_remote_reel(svc, fake):
    a = svc.run(submit(svc))
    b = svc.run(submit(svc))
    assert a is b
    assert len(fake.published_reels(PAGE)) == 1
    assert fake.calls.count(Phase.START) == 1


def test_comment_failure_is_independent_of_video_status(svc, fake):
    job = svc.run(submit(svc))
    svc.request_comment(job)
    fake.script(Phase.COMMENT, B.FAIL)
    svc.post_comment(job)
    assert job.status is V.PUBLISHED
    assert job.comment_status is CommentStatus.FAILED
    svc.post_comment(job)  # explicit retry of a definite failure is allowed
    assert job.comment_status is CommentStatus.POSTED


def test_comment_requires_published_video(svc, fake):
    fake.script(Phase.FINISH, B.TIMEOUT_NO_EFFECT)
    job = svc.run(submit(svc))
    with pytest.raises(InvalidTransition):
        svc.request_comment(job)
    assert job.comment_status is CommentStatus.NOT_REQUESTED


def test_comment_unknown_reconciles_to_existing_comment_without_duplicate(svc, fake):
    job = svc.run(submit(svc))
    svc.request_comment(job)
    fake.script(Phase.COMMENT, B.TIMEOUT_APPLIED)
    svc.post_comment(job)
    assert job.comment_status is CommentStatus.UNKNOWN
    with pytest.raises(ReconcileRequired):
        svc.post_comment(job)
    svc.reconcile_comment(job)
    assert job.comment_status is CommentStatus.POSTED
    assert len(fake.comments[job.remote_video_id]) == 1


def test_comment_unknown_not_found_after_window_fails_then_retry_posts_once(svc, fake, clock):
    job = svc.run(submit(svc))
    svc.request_comment(job)
    fake.script(Phase.COMMENT, B.TIMEOUT_NO_EFFECT)
    svc.post_comment(job)
    svc.reconcile_comment(job)
    assert job.comment_status is CommentStatus.UNKNOWN
    clock.advance(minutes=6)
    svc.reconcile_comment(job)
    assert job.comment_status is CommentStatus.FAILED
    svc.post_comment(job)
    assert job.comment_status is CommentStatus.POSTED
    assert len(fake.comments[job.remote_video_id]) == 1
