"""Automatically resumes a video that crashed mid-pipeline, instead of
leaving it to rot until a human notices and clicks Continue.

Built after a real incident: video_generation crashed on an unrelated bug
right after a scene's clip finished generating on Runpod. Nothing resumed
polling for it until a human noticed and clicked Continue almost an hour
later — by then Runpod had already dropped the finished result (it does
not hold one forever), so that scene's real GPU cost was paid again on the
retry. The gap between a crash and a human noticing is exactly the gap
that can turn a crash into a double-billed clip.

Mirrors services/scheduling/scheduler.py's check-and-act pattern exactly,
and reuses the SAME crashed-stage parsing as the manual Continue endpoint
(app/routers/videos.py's continue_video) — this is just that same resume
running itself on a timer instead of waiting for a click.

Capped at _MAX_AUTO_RETRIES per video (Video.auto_retry_count, reset on a
manual Restart/Continue) so a video that is persistently, not transiently,
broken stops auto-retrying and is left FAILED for a human to look at —
same as it is today — instead of quietly re-billing forever.

Runs inside apps/worker/worker.py via the same SchedulerRunner/APScheduler
background thread as the upload-schedule checker, in the same process.
"""

import re
from collections.abc import Callable

from sqlalchemy.orm import Session

_CHECK_INTERVAL_SECONDS = 30
_MAX_AUTO_RETRIES = 2
_CRASHED_AT = re.compile(r"Crashed at '([a-z_]+)'")


def check_and_retry_crashed_videos(db: Session) -> list[str]:
    """Runs one check pass. Returns a list of human-readable results (one
    per video it retried) — plain return value, not exceptions, so one bad
    video can't stop the others from being retried."""
    # Local imports: avoid an apps/api <-> services import cycle (same
    # reasoning as services/ai/orchestration/pipeline.py).
    from app.jobs.queue import enqueue_pipeline_start
    from app.models.enums import PipelineStage
    from app.models.video import Video

    not_resumable = {PipelineStage.TOPIC, PipelineStage.COMPLETED, PipelineStage.FAILED}

    candidates = (
        db.query(Video)
        .filter(Video.stage == PipelineStage.FAILED, Video.auto_retry_count < _MAX_AUTO_RETRIES)
        .all()
    )

    results = []
    for video in candidates:
        match = _CRASHED_AT.search(video.stage_detail or "")
        if match is None:
            continue
        try:
            resume_stage = PipelineStage(match.group(1))
        except ValueError:
            continue
        if resume_stage in not_resumable:
            continue

        video.auto_retry_count += 1
        video.stage = resume_stage
        video.stage_detail = (
            f"Auto-retrying after a crash (attempt {video.auto_retry_count}/{_MAX_AUTO_RETRIES})"
        )
        db.commit()
        enqueue_pipeline_start(video_id=video.id, run_research=False)
        results.append(f"video {video.id}: auto-retried at {resume_stage.value}")

    return results


class AutoRetryRunner:
    """Thin wrapper so apps/worker/worker.py can start/stop this with two
    lines, without the worker needing to know APScheduler exists. Takes
    the already-running scheduler from SchedulerRunner instead of starting
    a second background thread for one more periodic check."""

    def __init__(self, session_factory: Callable[[], Session], scheduler) -> None:
        self._session_factory = session_factory
        self._scheduler = scheduler

    def _tick(self) -> None:
        db = self._session_factory()
        try:
            check_and_retry_crashed_videos(db)
        finally:
            db.close()

    def start(self) -> None:
        self._scheduler.add_job(
            self._tick,
            "interval",
            seconds=_CHECK_INTERVAL_SECONDS,
            id="auto_retry_crashed_videos",
            replace_existing=True,
        )
