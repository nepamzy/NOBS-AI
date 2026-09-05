"""Background worker entry point (CLAUDE.md: apps/worker -> background
processing). Listens on the same queue the API enqueues to and runs jobs
from app.jobs.tasks (apps/api).

Run from the repo root so both `app` (apps/api) and `services` (repo root)
are importable:

    PYTHONPATH=apps/api:. python apps/worker/worker.py
"""

import redis
from app.config import settings
from app.jobs.queue import pipeline_queue
from rq import Worker

if __name__ == "__main__":
    conn = redis.from_url(settings.redis_url)
    worker = Worker([pipeline_queue], connection=conn)
    worker.work()
