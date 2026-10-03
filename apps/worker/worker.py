"""Background worker entry point (CLAUDE.md: apps/worker -> background
processing). Listens on both job queues the API enqueues to (video
pipeline + clipping pipeline, see app/jobs/queue.py) and runs jobs from
app.jobs.tasks / app.jobs.clip_tasks (apps/api). Also runs the
upload-schedule due-check (services/scheduling) in a background thread
alongside it — one process, one Render service, instead of separate ones
for each of these.

One process means a long clip transcription CAN sit ahead of a quick
video-pipeline stage advance (RQ drains queues in listed order, one job
at a time) — a known limitation, not something this version schedules
around; a second worker process is the real fix if that becomes a
problem in practice.

Run from the repo root so both `app` (apps/api) and `services` (repo root)
are importable:

    PYTHONPATH=apps/api:. python apps/worker/worker.py
"""

import redis
from app.config import settings
from app.db import SessionLocal
from app.jobs.queue import clip_queue, pipeline_queue
from rq import Worker

from services.scheduling.scheduler import SchedulerRunner

if __name__ == "__main__":
    scheduler = SchedulerRunner(SessionLocal)
    scheduler.start()

    conn = redis.from_url(settings.redis_url)
    worker = Worker([pipeline_queue, clip_queue], connection=conn)
    try:
        worker.work()
    finally:
        scheduler.stop()
