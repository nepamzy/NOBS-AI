# Mirrors the local dev setup in README.md (python apps/worker/worker.py) —
# not yet build-tested, see README's "Containers" section before relying on
# this for a real deployment. Reuses the API's requirements since the worker
# imports app.jobs.tasks (FastAPI/SQLAlchemy included) — see apps/worker's
# own comment about why apps/api needs to be on PYTHONPATH.
FROM python:3.11-slim

WORKDIR /repo

COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

COPY apps/api apps/api
COPY apps/worker apps/worker
COPY services services

ENV PYTHONPATH=/repo/apps/api:/repo

CMD ["python", "apps/worker/worker.py"]
