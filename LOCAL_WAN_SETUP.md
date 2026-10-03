# Running video generation on your own laptop GPU (free, instead of renting one)

## Why this exists

Your laptop has an 8GB-VRAM GPU and 560GB of storage. Renting a cloud GPU
(Runpod) costs real money per hour; your own GPU, sitting idle most of the
day, costs nothing extra. `Wan2.1-T2V-1.3B` — the smaller Wan model, not
the 14B one — is specifically sized to fit in ~8GB VRAM at 480p. That's a
real, workable match for the short 5-12s scene clips this pipeline
generates.

**The honest trade-off:** your laptop has to be on and running the server
below whenever a video is actively generating clips. If it's asleep or
closed, that video's generation just stays blocked — exactly like any
other not-yet-configured engine — until you open the laptop and start the
server. It will NOT silently fall back to a paid provider or fail
unpredictably; it parks itself and waits, same as every other engine in
this app.

**Speed:** roughly 4-6 minutes per 5-second 480p clip on an RTX 4060-class
8GB GPU (independently reported across multiple benchmarks — not
guaranteed for your exact card, but a reasonable expectation). A 5-scene,
5-minute video is maybe 20-30 minutes of GPU time total. Slower than a
rented A100, but $0.

## One-time setup on your laptop

1. Install Python 3.11+ and a CUDA-capable PyTorch build matching your GPU
   driver (see https://pytorch.org/get-started/locally/ — pick your OS and
   CUDA version).
2. Install the rest:
   ```
   pip install diffusers transformers accelerate fastapi uvicorn pydantic
   ```
3. The first request downloads the model (~5GB) from Hugging Face
   automatically — no separate download step, no account needed (the model
   is public).
4. Run the server:
   ```
   python scripts/local_wan_server.py
   ```
   It listens on port 8765. Leave this terminal running whenever you want
   generation to work.
5. Find your laptop's local network IP (e.g. `192.168.1.50` —
   `ipconfig`/`ifconfig` or your OS's network settings) if NOBS AI's
   backend needs to reach it over your home network rather than
   `localhost` (it will, since the backend runs on Render, not your
   laptop).

## Point NOBS AI at it

In Render's environment variables for both `nobs-ai-api` and the
Background Worker:

```
VIDEO_PROVIDER=wan_local
LOCAL_WAN_API_URL=http://<your-laptop-ip>:8765
```

**Important:** your laptop's port 8765 needs to actually be reachable from
Render's servers over the internet, not just your home network — that
typically means port-forwarding on your router, or a tunnel tool (e.g.
`ngrok`, `cloudflared`) pointed at `localhost:8765`, which is simpler and
doesn't require router configuration. Start with a tunnel; it costs
nothing at low usage and avoids exposing your home network directly.

## Switching back

Set `VIDEO_PROVIDER=wan_runpod` (and the existing `RUNPOD_API_KEY`/
`WAN_ENDPOINT_ID`) any time you'd rather rent a GPU instead — e.g. for a
higher-resolution or faster run. Nothing else in the app needs to change;
`services/video/factory.py` picks the engine from this one setting.
