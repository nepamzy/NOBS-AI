"""Background worker entry point (CLAUDE.md: apps/worker -> background
processing). Listens on the same queue the API enqueues to and runs jobs
from app.jobs.tasks (apps/api). Also runs the upload-schedule due-check
(services/scheduling) in a background thread alongside it — one process,
one Render service, instead of a second one just for cron-like checks.

Run from the repo root so both `app` (apps/api) and `services` (repo root)
are importable:

    PYTHONPATH=apps/api:. python apps/worker/worker.py
"""

import redis
from app.config import settings
from app.db import SessionLocal
from app.jobs.queue import pipeline_queue
from rq import Worker

from services.scheduling.scheduler import SchedulerRunner

if __name__ == "__main__":
    scheduler = SchedulerRunner(SessionLocal)
    scheduler.start()

    conn = redis.from_url(settings.redis_url)
    worker = Worker([pipeline_queue], connection=conn)
    try:
        worker.work()
    finally:
        scheduler.stop()
