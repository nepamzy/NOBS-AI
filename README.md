# NOBS AI

Personal YouTube automation pipeline (V1): `Topic → Research → Script →
Storyboard → Approval → Video (Wan) + Voice (Chatterbox) → FFmpeg Assembly →
Captions → Thumbnail → Final MP4`.

Full product/architecture context, and the non-negotiable cost/approval
rules Claude Code operates under in this repo, are in `CLAUDE.md` — read
that before making changes here.

**Current status:** Stage 3, backend foundation. Database schema, API
skeleton, job queue, and the AI/video/voice engine abstraction layers are in
place. No LLM provider, Runpod, or Chatterbox server is configured — every
paid-action adapter raises a clear approval-required error instead of
calling anything, by design.

## Layout

```
apps/
  api/       FastAPI backend: models, routers, job queue, Alembic migrations
  worker/    RQ worker process that runs the pipeline jobs the API enqueues
services/
  ai/        research + script engines (LLM-backed, not yet configured),
             and the orchestration state machine that drives a Video
             through the pipeline one stage at a time
  video/     VideoEngine abstraction + Wan/Runpod adapter (paid, gated)
  voice/     VoiceEngine abstraction + Chatterbox adapter (self-hosted, gated)
  rendering/ FFmpeg assembly (local, free, real implementation)
  storage/   Storage abstraction, local filesystem backend by default
```

## Running locally

Requires Postgres and Redis. Either via Docker:

```
docker compose up -d
```

...or point `DATABASE_URL`/`REDIS_URL` in `.env` at local installs.

```
cp .env.example .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt

export PYTHONPATH=apps/api:.

# Apply the schema
cd apps/api && alembic upgrade head && cd ../..

# API
PYTHONPATH=apps/api:. uvicorn app.main:app --reload --app-dir apps/api --port 8000

# Worker (separate terminal)
PYTHONPATH=apps/api:. python apps/worker/worker.py
```

`GET /health` should return `{"status": "ok"}`.

## What actually runs vs. what's gated

- **Free and real:** the API, database schema, job queue, and FFmpeg
  assembly code.
- **Gated behind an approval:** any call to an LLM (research/script), Wan
  (video generation via Runpod), or Chatterbox (voice). Each adapter raises
  `ApprovalRequiredError` with a filled-in cost warning instead of making
  the call, until the relevant env vars are set *and* Nobert has approved
  that spend (see `CLAUDE.md` Part 1).
