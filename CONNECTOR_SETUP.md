# Claude connector — hand a finished video to NOBS AI

Lets a Claude session that has already made a video (script, footage, voiceover)
file it into NOBS AI. It arrives as a **completed project with every pipeline
step ticked**, waiting for you to review it and publish it yourself.

**What it can do:** import a finished MP4 (+ optional script scenes, voiceover,
captions, thumbnail), list projects/videos, read a video's status.
**What it can never do:** publish, upload to YouTube, schedule, delete, or spend
money. No tool for any of those exists behind the connector key — publishing
stays a click you make in NOBS AI (CLAUDE.md Part 1).

Cost: **$0**. Nothing is generated — it only downloads, stores and records files.

## 1. Deploy and migrate

Pushing this to the deploy branch runs `alembic upgrade head` on boot, which
adds the `connector_keys` table. Make sure `API_BASE_URL` on Render is the API's
real public URL (e.g. `https://nobs-ai-api.onrender.com`).

## 2. Create your connector link

NOBS AI → **Channel Connections** → **Claude** → **New connector link**.
The link is shown **once** (only a hash is stored). Copy it. Treat it like a
password: anyone holding it can add videos to your account. **Revoke** kills it
instantly.

## 3. Add it to Claude

Claude → Settings → Connectors → **Add custom connector** → paste the link.
(Custom connectors aren't on every Claude plan — check yours.) Anthropic's
servers call the link, so the API must be publicly reachable.

## 4. Use it

In the Claude session that makes your videos, tell it, e.g.:
*"When the video is done, send it to NOBS AI with nobs_import_video."*

- If the MP4 has a public https link: it calls `nobs_import_video` with `video_url`.
- If the MP4 only exists in Claude's sandbox: it calls `nobs_upload_instructions`
  and uploads with the returned `curl` command (needs the sandbox to be able to
  reach your API host).

Limits: MP4 only, max 50 MB (`CONNECTOR_MAX_IMPORT_MB`; Supabase's free tier
rejects bigger files). Links must be https to a public host — private/loopback
addresses are refused.

## Security notes (honest ones)

- The key is in the URL because that is all a Claude custom-connector link can
  carry. The API redacts it from its own access logs. Don't paste the link into
  chats, screenshots or repos. If it leaks: Revoke, create a new one.
- Keys are admin-only to create and are scoped to your account.
- The upgrade path, if you ever want more than a secret link, is OAuth on the
  connector — not built.

## Not built yet

- **Scheduling a video for another day.** Publishing today is a manual click;
  per-video scheduled publishing would use YouTube's `publishAt`, which flips a
  video public on a timer — externally visible, so it needs your explicit go-ahead
  before it's built.
- Verified against raw JSON-RPC calls and the test suite, **not yet against the
  real Claude custom-connector UI.** Expect to test that first connection yourself.
