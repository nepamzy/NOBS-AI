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


def enqueue_pipeline_start(video_id: uuid.UUID, run_research: bool) -> str:
    """Push a pipeline-advance job onto the queue for apps/worker to pick up.
    Returns the RQ job id. Raises if Redis is unreachable — the API surfaces
    that as a 5xx rather than silently dropping the job."""
    job = pipeline_queue.enqueue(
        "app.jobs.tasks.advance_pipeline",
        str(video_id),
        run_research,
    )
    return job.id


def enqueue_clip_pipeline_start(source_video_id: uuid.UUID) -> str:
    job = clip_queue.enqueue(
        "app.jobs.clip_tasks.advance_clip_pipeline",
        str(source_video_id),
    )
    return job.id
