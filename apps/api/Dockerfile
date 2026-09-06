# Mirrors the local dev setup in README.md (pip install -r requirements.txt,
# uvicorn app.main:app) — not yet build-tested, see README's "Containers"
# section before relying on this for a real deployment.
FROM python:3.11-slim

WORKDIR /repo

COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

COPY apps/api apps/api
COPY services services

WORKDIR /repo/apps/api
ENV PYTHONPATH=/repo/apps/api:/repo

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
