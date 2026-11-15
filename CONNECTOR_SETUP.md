# Claude connector — hand a finished video to NOBS AI

Lets a Claude session that has already made a video (script, footage, voiceover)
file it into NOBS AI. It arrives as a **completed project with every pipeline
step ticked**, waiting for you to review it and publish it yourself.

**What it can do:**
- import a finished MP4 (+ optional script scenes, voiceover, captions, thumbnail);
- **produce a video you approved in NOBS AI** (see "Let Claude produce it" below);
- list projects/videos and read a video's status;
- **schedule a video for a date and time, or publish it now — only when you tell
  Claude to, for that exact video.** `nobs_publish_video` also requires
  `confirm=true`; the tool descriptions and the server instructions tell Claude never
  to do either on its own. Uploads are always private first.

**What it can never do:** delete anything, change settings, or spend money.
There is no tool for any of those behind the connector key.

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

## Let Claude produce it (choose Claude or Runpod)

On **Create Video** pick **"Who makes the voice and video?"**:
- **NOBS AI (Runpod)** — the existing pipeline (paid GPU + voice, each step gated).
- **My Claude session** — you write or generate the script as usual and approve the
  script and storyboard. NOBS AI then **stops at "Waiting for Claude"** and spends
  nothing on Runpod/voice.

The connector is **pull-based**: NOBS AI can't push into a Claude chat. Open your
Claude session and say *"check NOBS AI for jobs to produce"*. It calls
`nobs_list_claude_jobs`, then `nobs_get_claude_job` (script as scenes, narration,
visual prompts, chosen voice and style, suggested YouTube title/description), makes
the voiceover and footage, and returns the MP4 with `nobs_complete_claude_job` (or the
upload command, adding `video_id`). The video then shows as Completed.

## Schedule or publish (the calendar)

- **In the app:** open a finished video → **Publish on a date** → pick date and time
  (in your own time zone) → Schedule. The **Publishing** page has a month calendar of
  everything scheduled. A scheduled video uploads privately and goes public at that
  moment.
- **By telling Claude:** *"Schedule video X for 1 December at 5pm Lagos time."* Claude
  must give an exact time **with a time zone** (a bare "5pm" is rejected). *"Publish
  video X now."* publishes immediately.
- The worker checks every minute. If the worker was down at the time, it publishes
  late (on its next check) rather than skipping. If YouTube rejects it, the schedule is
  cleared (never retried every minute) and the video page shows why.
- Needs YouTube connected (`YOUTUBE_SETUP.md`). Without it, scheduling/publishing is
  refused with a clear message.

## Clips: Claude cuts them, NOBS AI uploads them

Claude can do the clipping itself: it finds the moments in a long video, cuts them in
its own sandbox, then hands each finished clip over with `nobs_submit_clip` (a public
https link) or the `clip_command` from `nobs_upload_instructions` (direct upload).
NOBS AI files each clip on the **Smart Clipping** page, grouped by the long video's
title, and **uploads it to YouTube as private**.

- **Format (you tell Claude, every time):** each clip is either a **Short** — vertical
  9:16, up to **3 minutes** — or a **long video** — horizontal, any length that fits the
  size limit. Claude must be told which; if you haven't said, it asks. NOBS AI checks the
  file's real shape and length and rejects a wrong one with a fix hint (e.g. the ffmpeg
  crop-to-9:16 command), because YouTube decides Short vs. normal video from the picture,
  not from a label. Shorts get `#Shorts` added to the description.
- **Which channel:**
  - **Clips channel = vertical Shorts only.** Tell Claude "clips channel"; a long video
    is refused there.
  - **Main channel = Short or long.** Tell Claude "main channel, short" or "main channel,
    long".
  - If you give no channel: a Short goes to the main channel if connected, else the clips
    channel; a long video goes to the main channel only. An explicit channel that isn't
    connected is refused, never swapped. A clip stays on the channel it was uploaded to.
- **Length (you tell Claude):** e.g. "2-minute", "3-minute" or "5-minute" clips. Shorts
  stop at 3 minutes (checked against several sources, not YouTube's own page), so a
  **5-minute clip can only be a long video** on the main channel.
- **Size limit:** 50 MB per file (Supabase's free tier). A 5-minute horizontal clip at
  normal quality is bigger than that, so Claude is told to encode small (720p, crf ~28).
  If a long clip still doesn't fit, raising `CONNECTOR_MAX_IMPORT_MB` needs a paid
  Supabase plan — your call.
- **Public only when you say so:** `publish=true` on the submit, or `nobs_publish_clip`
  (needs `confirm=true`), and only when you told Claude to publish clips. Otherwise
  publish from the Smart Clipping page.
- **A failed upload never loses the clip.** If YouTube isn't connected or rejects it,
  the clip is still stored, and Claude is told exactly why.
- The page shows each clip's status: "Private · main channel", "Published · second
  channel".
- Separate from NOBS AI's own automatic clipping (upload a video; it transcribes and picks
  moments itself), which still needs an LLM key and is unchanged.

## Not built / not verified

- **Not tried from the real Claude custom-connector UI** — verified with raw protocol
  calls, a live local worker and browser, and the test suite.
- A real publish to YouTube hasn't been done: YouTube isn't connected yet. The
  failure path (bad credentials) was exercised live; the success path is tested
  with a stand-in YouTube client only.
- Switching a video from Claude to Runpod after the fact isn't built.
- Clips: 50 MB per clip (file-size ceiling); a real upload to YouTube hasn't happened
  (not connected). The Google-rejection path was exercised live.
