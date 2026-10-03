# Running voice generation on self-hosted Chatterbox (free, instead of ElevenLabs)

## Why this exists

Chatterbox (Resemble AI, MIT license) is free to run yourself — no per-call
cost like ElevenLabs. The trade-off is the same one `wan_local` has: a
server has to actually be running whenever a video is generating
narration. This uses `devnen/Chatterbox-TTS-Server` on GitHub, a
ready-made self-hosted server with an OpenAI-compatible API.

## One-time setup

You can run this on the same GPU you're using for `wan_local` (one at a
time is fine — video and voice generation happen at different pipeline
stages, not simultaneously), or on CPU if you don't mind it being slower.

1. Clone and set up the server:
   ```
   git clone https://github.com/devnen/Chatterbox-TTS-Server
   cd Chatterbox-TTS-Server
   pip install -r requirements.txt
   ```
   (see that repo's own README for the exact CUDA/CPU setup for your
   hardware — it supports NVIDIA, AMD, and CPU)
2. Add a voice. Chatterbox needs a reference audio file to clone a voice
   from, or you can use one of its predefined voices out of the box. Drop
   a short (10-30s), clean voice recording into the server's voices
   folder (see its README for the exact path) if you want your own voice
   or a specific cloned voice, rather than a generic predefined one.
3. Start the server (see that repo's README for the exact run command —
   typically `python server.py` or similar). It listens on a port (often
   8000 or 7860 — check its startup log).
4. Note the voice filename you want to use (predefined or the one you
   just added) — you'll map it to a `voice_preset` id in step 2 below.

## Point NOBS AI at it

In Render's environment variables for both `nobs-ai-api` and the
Background Worker:

```
VOICE_PROVIDER=chatterbox
CHATTERBOX_API_URL=http://<your-server-ip>:<port>
CHATTERBOX_VOICE_MAP={"warm-narrator":"<voice-filename>.wav"}
```

`CHATTERBOX_VOICE_MAP` maps each of NOBS AI's own voice_preset ids
(`services/voice/catalog.py`) to a voice filename Chatterbox knows about.
Only presets listed here will work — an unmapped preset blocks with a
clear "no Chatterbox voice file mapped" error, same pattern as every
other unconfigured engine in this app.

**Important — same reachability issue as `wan_local`:** if you're running
the Chatterbox server on your own laptop (not a separate rented box),
Render's servers need to reach it over the internet, not just your home
network. Use a tunnel (`ngrok`, `cloudflared`) pointed at your server's
port — same approach as `LOCAL_WAN_SETUP.md` — rather than opening a port
on your router directly.

## What NOBS AI does with it

Chatterbox's own API only returns raw audio — no word-by-word timing the
way ElevenLabs' `/with-timestamps` endpoint gives. Burned-in captions and
duration-based video syncing both need real word timestamps, so
`ChatterboxEngine` runs the generated audio back through the same free
local `faster-whisper` transcription already built for the clipping
feature, measuring real word timings rather than guessing them. This adds
a few seconds of CPU transcription time per scene's narration — no extra
cost, just a bit of processing time on top of generation itself.

## Switching back

Set `VOICE_PROVIDER=elevenlabs` (and `ELEVENLABS_API_KEY`/
`ELEVENLABS_VOICE_MAP`) any time you'd rather use the managed, no-server
option instead. `services/voice/factory.py` picks the engine from this
one setting — nothing else in the app needs to change.
