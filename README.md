# NOBS AI

Personal YouTube automation pipeline (V1): `Topic → Research → Script →
Storyboard → Approval → Video (Wan) + Voice (Chatterbox) → FFmpeg Assembly →
Captions → Thumbnail → Final MP4`.

Full product/architecture context, and the non-negotiable cost/approval
rules Claude Code operates under in this repo, are in `CLAUDE.md` — read
that before making changes here.

**Live:**
- Frontend: https://nobs-ai.vercel.app (Vercel)
- API: https://nobs-ai-api.onrender.com (Render)
- Database + file storage: Supabase
- Job queue: Redis Cloud
- Background worker + web API both run on Render

**Current status:** Far past Stage 3. The full pipeline (auth, multi-user
accounts with admin-issued signup PINs, the Create Video flow, Storyboard
review, the admin/video assistant chat, YouTube upload+publish, weekly
upload schedules with opt-in automation, the Smart Clipping feature, and an
in-app Spend dashboard) is built and hosted. Research/Script generation use
a real Anthropic key. `ChatterboxEngine` and `WanEngine` are code-complete
but still waiting on their actual servers to exist — see **Remaining Work**.

## Remaining work

Roughly in priority order:

1. **Fix the API's Start Command on Render.** `nobs-ai-api`'s start command
   lost its `PYTHONPATH` across the `&&` chain after `alembic upgrade head`
   was added to it — the shell only applies `VAR=val` to the one command
   right after it, not the rest of the chain. It should read:
   ```
   cd apps/api && export PYTHONPATH=.:../.. && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   (the `export` is what's missing). Without this the API crash-loops on
   `ModuleNotFoundError: No module named 'services'` and nothing — including
   login — works at all. **This is the current blocker as of 2026-10-09.**
2. **Confirm Vercel Deployment Protection (SSO) is off.** If it's still on,
   `nobs-ai.vercel.app` challenges anyone who isn't logged into the Vercel
   account that owns the project — meaning nobody Nobert invites can reach
   even the login page. Flagged, not yet confirmed resolved.
3. **Connect a voice engine.** `ChatterboxEngine` is implemented against
   `devnen/Chatterbox-TTS-Server`'s real API, but needs that server actually
   running somewhere reachable (`CHATTERBOX_API_URL`) — see
   `CHATTERBOX_SETUP.md`. In progress: self-hosting it on Nobert's own PC.
4. **Connect a video engine.** `WanEngine` (Runpod) or the free
   `wan_local` adapter (Nobert's own GPU) needs the corresponding env vars
   set — see `LOCAL_WAN_SETUP.md`. Not started.
5. **Second YouTube channel OAuth for Smart Clipping.** The Clips feature
   publishes to a separate channel from the main one and needs its own
   OAuth client (`CLIPS_YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN`) — same
   process as `YOUTUBE_SETUP.md`, just against the other channel. Not done.
6. **A real end-to-end pipeline run.** Once #1-#2 are fixed, create a real
   project and confirm it actually reaches Topic → Research → Script →
   Storyboard and correctly stops there for approval — this exercises the
   live LLM key for the first time outside of chat. Not yet verified live.
7. **Live-test the admin → PIN → signup flow.** Generate a real PIN, sign
   up a guest account, confirm it works end to end. Not yet verified live.
8. **Decide a guest video-duration/token policy before broader invites.**
   `target_duration_seconds` has no cap and token cost doesn't scale with
   it — a 3-minute and a 30-minute video both cost a guest 1 token despite
   very different real spend to Nobert.

## Layout


```
apps/
  api/       FastAPI backend: models, routers, job queue, Alembic migrations
  worker/    RQ worker process that runs the pipeline jobs the API enqueues
  web/       React + Vite + Tailwind frontend (Dashboard/Create/Projects/
             Storyboard) against the API
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

```
# Frontend (separate terminal)
cd apps/web
npm install
npm run dev
```

Open http://localhost:5173. `apps/web/.env.development` points it at
`http://localhost:8000` by default; the API's `CORS_ORIGINS` (`.env.example`)
must include the frontend's origin.

## Tests

```
pip install -r apps/api/requirements-dev.txt
cd apps/api && pytest
```

Tests create and drop a throwaway `nobs_ai_test` database on the same
Postgres server as `DATABASE_URL` (never touching `nobs_ai` itself), so a
reachable Postgres is the only thing they need — no Redis, no worker, no LLM
config. Job enqueueing is stubbed out in API tests.

## Containers (prepared, not build-tested)

`apps/api/Dockerfile` and `apps/worker/Dockerfile` exist, mirroring the
local dev setup above exactly (same requirements.txt, same PYTHONPATH
layout). **They have not been through a real `docker build`** — this
sandbox has no Docker daemon to verify against, so treat them as a
starting point, not a validated deployment path. Build from the repo root
so the build context includes `services/`:

```
docker build -f apps/api/Dockerfile -t nobs-ai-api .
docker build -f apps/worker/Dockerfile -t nobs-ai-worker .
```

## Tests

- **Free and real:** the API, database schema, job queue, and FFmpeg
  assembly code.
- **Gated behind an approval:** any call to an LLM (research/script), Wan
  (video generation via Runpod), or Chatterbox (voice). Each adapter raises
  `ApprovalRequiredError` with a filled-in cost warning instead of making
  the call, until the relevant env vars are set *and* Nobert has approved
  that spend (see `CLAUDE.md` Part 1).
