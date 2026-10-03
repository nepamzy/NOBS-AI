"""Reference local Wan 2.1 inference server — run this on YOUR OWN laptop
(with its GPU), not on Render. NOBS AI's backend (cloud) talks to this over
the network via LOCAL_WAN_API_URL. See LOCAL_WAN_SETUP.md for setup.

This is a standalone script, not part of the deployed app — it has its own
dependencies (torch, diffusers, fastapi, uvicorn) that don't belong in
apps/api/requirements.txt, since they only need to exist on your laptop.

Contract this must satisfy (see services/video/local_wan/adapter.py):
    POST /generate  {"prompt": str, "duration_seconds": int}
      -> 200, body = raw mp4 bytes, header "X-Clip-Duration-Seconds": <float>

One request at a time is fine — NOBS AI's pipeline already generates scene
clips for one video sequentially, so this script makes no attempt at
concurrency or a job queue; keeping it simple keeps it correct.

Uses Wan-AI/Wan2.1-T2V-1.3B-Diffusers — the variant sized for ~8GB VRAM
cards (confirmed: the HF model card and multiple independent benchmarks
cite ~8.2GB for this checkpoint at 480p; 720p needs 16-20GB and isn't
offered here on purpose). A 5s clip takes roughly 4-6 minutes on an
RTX 4060-class 8GB laptop GPU — much slower than a rented A100, free
otherwise.
"""

import io

import torch
import uvicorn
from diffusers import AutoencoderKLWan, WanPipeline
from diffusers.utils import export_to_video
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel

_MODEL_ID = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
_FPS = 15
_NEGATIVE_PROMPT = (
    "Bright tones, overexposed, static, blurred details, subtitles, style, "
    "works, paintings, images, static, overall gray, worst quality, low "
    "quality, JPEG compression residue, ugly, incomplete, extra fingers, "
    "poorly drawn hands, poorly drawn faces, deformed, disfigured"
)

app = FastAPI(title="Local Wan 2.1 server (reference)")
_pipe: WanPipeline | None = None


class GenerateRequest(BaseModel):
    prompt: str
    duration_seconds: int = 5


def _load_pipeline() -> WanPipeline:
    """Loaded once, lazily, on first request — not at import time, so the
    server starts instantly and the ~5GB model download only happens when
    actually needed."""
    global _pipe
    if _pipe is None:
        vae = AutoencoderKLWan.from_pretrained(
            _MODEL_ID, subfolder="vae", torch_dtype=torch.float32
        )
        _pipe = WanPipeline.from_pretrained(_MODEL_ID, vae=vae, torch_dtype=torch.bfloat16)
        _pipe.to("cuda")
    return _pipe


def _frame_count_for(duration_seconds: int) -> int:
    """Wan's frame count must be 4k+1 (diffusers docs). Rounds the
    requested duration to the nearest valid value, minimum one step (5
    frames, ~0.3s) so a very short request never asks for zero frames."""
    raw_frames = round(duration_seconds * _FPS)
    k = max(1, round((raw_frames - 1) / 4))
    return 4 * k + 1


@app.post("/generate")
def generate(request: GenerateRequest) -> Response:
    pipe = _load_pipeline()
    num_frames = _frame_count_for(request.duration_seconds)

    output = pipe(
        prompt=request.prompt,
        negative_prompt=_NEGATIVE_PROMPT,
        height=480,
        width=832,
        num_frames=num_frames,
        guidance_scale=5.0,
    ).frames[0]

    buffer = io.BytesIO()
    # export_to_video needs a real path, not a buffer — write to a temp
    # file then read it back, since diffusers doesn't offer an in-memory
    # path for this.
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = str(Path(tmp_dir) / "clip.mp4")
        export_to_video(output, tmp_path, fps=_FPS)
        buffer.write(Path(tmp_path).read_bytes())

    actual_duration = num_frames / _FPS
    return Response(
        content=buffer.getvalue(),
        media_type="video/mp4",
        headers={"X-Clip-Duration-Seconds": str(actual_duration)},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
