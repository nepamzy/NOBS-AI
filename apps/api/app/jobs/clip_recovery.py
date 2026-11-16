"""Puts Smart Clipping uploads back on the queue after the worker was restarted
mid-job. A killed job leaves no error behind, so without this an upload sits at
"Queued" forever. Runs once when the worker starts (see apps/worker/worker.py).
Bounded by SourceVideo.attempts, so a job that keeps killing the worker is
retried a few times and then reported, never looped."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.jobs.clip_tasks import GIVE_UP_MESSAGE, MAX_ATTEMPTS
from app.jobs.queue import enqueue_clip_pipeline_start
from app.models.enums import ClipJobStage
from app.models.source_video import SourceVideo

logger = logging.getLogger(__name__)

# Anything touched more recently than this may simply be waiting its turn in the
# queue (or running on a worker that is still shutting down) — leave it alone.
_QUIET_PERIOD = timedelta(minutes=2)
_ACTIVE = (
    ClipJobStage.UPLOADED,
    ClipJobStage.TRANSCRIBING,
    ClipJobStage.SELECTING_CLIPS,
    ClipJobStage.EXTRACTING,
)


def requeue_interrupted_source_videos(db: Session) -> list[str]:
    cutoff = datetime.now(UTC) - _QUIET_PERIOD
    rows = (
        db.query(SourceVideo)
        .filter(
            SourceVideo.stage.in_(_ACTIVE),
            # A non-empty stage_detail means it stopped on purpose and says why
            # (needs an LLM key, no audio...) — nothing to resume.
            SourceVideo.stage_detail == "",
            SourceVideo.updated_at < cutoff,
        )
        .all()
    )
    results = []
    for source_video in rows:
        if source_video.attempts >= MAX_ATTEMPTS:
            source_video.stage_detail = GIVE_UP_MESSAGE
            db.commit()
            results.append(f"{source_video.id}: gave up")
            continue
        # Mark it touched first, so a second restart moments later doesn't queue it twice.
        source_video.updated_at = datetime.now(UTC)
        db.commit()
        enqueue_clip_pipeline_start(source_video.id)
        results.append(f"{source_video.id}: re-queued")
    return results
