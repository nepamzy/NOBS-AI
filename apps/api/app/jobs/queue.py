import uuid

import redis
from rq import Queue

from app.config import settings

_redis_conn = redis.from_url(settings.redis_url)
pipeline_queue = Queue("nobs-ai-pipeline", connection=_redis_conn)
# Separate queue: a long CPU-bound transcription shouldn't sit ahead of a
# quick video-generation stage advance, or vice versa — see
# apps/worker/worker.py, which listens to both with one process for now.
clip_queue = Queue("nobs-ai-clips", connection=_redis_conn)


# RQ's default is 180 seconds, which a single GPU clip can exceed (Runpod polls
# up to 10 minutes per clip). Stage progress is saved as it goes, so a long
# run is safe; this only stops a genuinely stuck job after 4 hours.
_JOB_TIMEOUT_SECONDS = 4 * 60 * 60


def enqueue_pipeline_start(video_id: uuid.UUID, run_research: bool) -> str:
    """Push a pipeline-advance job onto the queue for apps/worker to pick up.
    Returns the RQ job id. Raises if Redis is unreachable — the API surfaces
    that as a 5xx rather than silently dropping the job."""
    job = pipeline_queue.enqueue(
        "app.jobs.tasks.advance_pipeline",
        str(video_id),
        run_research,
        job_timeout=_JOB_TIMEOUT_SECONDS,
    )
    return job.id


def enqueue_clip_pipeline_start(source_video_id: uuid.UUID) -> str:
    job = clip_queue.enqueue(
        "app.jobs.clip_tasks.advance_clip_pipeline",
        str(source_video_id),
        job_timeout=_JOB_TIMEOUT_SECONDS,
    )
    return job.id
