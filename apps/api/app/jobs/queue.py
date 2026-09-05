import uuid

import redis
from rq import Queue

from app.config import settings

_redis_conn = redis.from_url(settings.redis_url)
pipeline_queue = Queue("nobs-ai-pipeline", connection=_redis_conn)


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
