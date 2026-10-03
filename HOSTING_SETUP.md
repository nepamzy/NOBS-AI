# Getting the hosted backend fully live on Render

Supabase (Postgres + Storage) and Vercel (frontend) are already live on
their free tiers. Render hosts the API and the background worker that
actually runs pipeline jobs. This is the one remaining piece to wire up.

## 1. Redis — job queue + rate limiting

Redis is what lets the API hand a video-generation job to the background
worker and return immediately, instead of making your browser wait
through the whole pipeline. It also backs simple rate limiting on
login/signup/chat. It is not optional, but it doesn't have to be a paid
Render add-on.

**Use Redis Cloud's free tier instead of Render's paid Redis** (saves
$10/month — more than enough headroom for a single-user job queue):

1. Go to https://redis.io/try-free, sign up, no card required
2. Create a free database (30MB, shared infra — plenty for this app's
   actual Redis usage)
3. Copy its connection string (`rediss://default:<password>@<host>:<port>`)
4. That's your `REDIS_URL`

## 2. Add environment variables to Render

In Render's dashboard, for **both** the `nobs-ai-api` Web Service and the
Background Worker (step 3 below) — these need to match on both services:

```
DATABASE_URL=<Supabase connection string, from Supabase dashboard -> Project Settings -> Database>
SUPABASE_SERVICE_ROLE_KEY=<Supabase dashboard -> Project Settings -> API>
SUPABASE_URL=<same place>
SUPABASE_STORAGE_BUCKET=nobs-ai
STORAGE_BACKEND=supabase
REDIS_URL=<from step 1 above>
```

Plus whichever engine credentials apply once you've set those up — see
`YOUTUBE_SETUP.md`, `LOCAL_WAN_SETUP.md`, `CHATTERBOX_SETUP.md`, and the
`LLM_PROVIDER`/`LLM_API_KEY` lines in `.env.example`.

Never paste these into chat with me — add them directly in Render's
dashboard, per this project's own credentials rule.

## 3. Create the Background Worker (manual — no API for this service type)

In Render's dashboard:
1. New → Background Worker
2. Connect the same GitHub repo
3. Build command: same as the API's (`pip install -r apps/api/requirements.txt`)
4. Start command: `PYTHONPATH=apps/api:. python apps/worker/worker.py`
5. Add all the same environment variables as step 2

Without this, videos (and clips) will sit stuck at "processing" forever —
the API only enqueues jobs, this is what actually runs them.

## 4. Confirm Supabase is actually reachable

Open the Supabase dashboard directly (not just via an API call) — this
project has hit Supabase's hibernation behavior repeatedly, where opening
the project in the dashboard wakes it when API calls alone don't. Once
it's confirmed reachable, pending database migrations can be applied.

## 5. Verify end to end

Once all of the above is in place, ask me to walk through a real test —
create a project, request a short video, approve the storyboard, and
watch it actually move through voice → video → assembly → captions →
thumbnail → completed, rather than assuming it works from config alone.
