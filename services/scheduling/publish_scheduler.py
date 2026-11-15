"""Publishes videos whose scheduled_publish_at has arrived (set from the app
or by Claude through the connector — see app/publishing.py).

Runs once a minute in the worker's background thread, sharing the scheduler
that apps/worker/worker.py already starts. Outcomes:
  * success  -> the video is public, the schedule is cleared;
  * failure  -> the schedule is cleared (so it is never retried every minute
    forever) and the reason is saved in video.publish_error, which the video
    page shows, so Nobert sees it and decides what to do.
A worker that was down at the scheduled time publishes late, on its next tick,
rather than skipping the video.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 60


def publish_due_videos(db: Session) -> list[str]:
    from app.models.video import Video
    from app.publishing import PublishingError, publish_now

    now = datetime.now(UTC)
    # skip_locked: if two ticks ever overlap, the second ignores rows the first
    # is already publishing instead of publishing twice.
    due = (
        db.query(Video)
        .filter(
            Video.scheduled_publish_at.isnot(None),
            Video.scheduled_publish_at <= now,
            Video.youtube_published.is_(False),
        )
        .with_for_update(skip_locked=True)
        .all()
    )

    results = []
    for video in due:
        video_id = video.id
        try:
            publish_now(db, video)
            results.append(f"video {video_id}: published on schedule")
        except PublishingError as exc:
            # Raised before anything is written (each step commits on its own).
            _record_failure(db, video_id, str(exc))
            results.append(f"video {video_id}: scheduled publish failed ({exc})")
        except Exception as exc:  # noqa: BLE001 - one video must not stop the others
            logger.exception("Scheduled publish crashed for video %s", video_id)
            db.rollback()
            _record_failure(db, video_id, f"{type(exc).__name__}: {exc}")
            results.append(f"video {video_id}: scheduled publish crashed ({exc})")
    return results


def _record_failure(db: Session, video_id, message: str) -> None:
    from app.models.video import Video

    video = db.get(Video, video_id)
    if video is None:
        return
    video.scheduled_publish_at = None
    video.publish_error = f"Scheduled publish failed: {message}"
    db.commit()


class PublishSchedulerRunner:
    def __init__(self, session_factory: Callable[[], Session], scheduler) -> None:
        self._session_factory = session_factory
        self._scheduler = scheduler

    def _tick(self) -> None:
        db = self._session_factory()
        try:
            publish_due_videos(db)
        finally:
            db.close()

    def start(self) -> None:
        self._scheduler.add_job(
            self._tick,
            "interval",
            seconds=_CHECK_INTERVAL_SECONDS,
            id="publish_due_videos",
            replace_existing=True,
        )
