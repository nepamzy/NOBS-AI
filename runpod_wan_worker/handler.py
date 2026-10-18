"""Runpod Serverless worker for Wan 2.1 text-to-video (1.3B).

Deployed from this repo on Runpod (Serverless -> New Endpoint -> GitHub repo,
Dockerfile in runpod_wan_worker/). Contract, matching services/video/wan/adapter.py:

    input:  {"prompt": str, "duration_seconds": int}
    output: {"clip_base64": str, "duration_seconds": float, "width": int, "height": int}

The clip comes back inside the response as base64 MP4, so this worker needs no
storage keys and no external bucket. A 5-second 480p clip is small enough for that.

Model: Wan-AI/Wan2.1-T2V-1.3B-Diffusers. The 1.3B checkpoint is chosen because it
fits in 16GB VRAM with room to spare (the 14B model is tight on 16GB). The weights
are downloaded at Docker build time (see Dockerfile) so a cold worker doesn't
spend billed GPU time downloading ~5GB.

This file has NOT been run on a GPU yet. The first real run is the paid test.
"""

import base64
import io
import tempfile
from pathlib import Path

import runpod
import torch
from diffusers import AutoencoderKLWan, WanPipeline
from diffusers.utils import export_to_video

_MODEL_ID = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
_FPS = 15
_WIDTH = 832
_HEIGHT = 480
_NEGATIVE_PROMPT = (
    "Bright tones, overexposed, static, blurred details, subtitles, style, "
    "works, paintings, images, static, overall gray, worst quality, low "
    "quality, JPEG compression residue, ugly, incomplete, extra fingers, "
    "poorly drawn hands, poorly drawn faces, deformed, disfigured"
)

_pipe: WanPipeline | None = None


def _load_pipeline() -> WanPipeline:
    """Loaded once per worker, on the first job, then reused for later jobs."""
    global _pipe
    if _pipe is None:
        vae = AutoencoderKLWan.from_pretrained(_MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
        _pipe = WanPipeline.from_pretrained(_MODEL_ID, vae=vae, torch_dtype=torch.bfloat16)
        _pipe.to("cuda")
    return _pipe


def _frame_count_for(duration_seconds: int) -> int:
    """Wan needs a frame count of 4k+1. Round the requested length to the nearest valid one."""
    raw_frames = round(duration_seconds * _FPS)
    k = max(1, round((raw_frames - 1) / 4))
    return 4 * k + 1


def handler(job: dict) -> dict:
    job_input = job.get("input") or {}
    prompt = job_input.get("prompt")
    if not prompt:
        return {"error": "missing 'prompt'"}
    duration_seconds = int(job_input.get("duration_seconds", 5))

    pipe = _load_pipeline()
    num_frames = _frame_count_for(duration_seconds)
    output = pipe(
        prompt=prompt,
        negative_prompt=_NEGATIVE_PROMPT,
        height=_HEIGHT,
        width=_WIDTH,
        num_frames=num_frames,
        guidance_scale=5.0,
    ).frames[0]

    # export_to_video needs a file path, so write to a temp folder and read it back.
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = str(Path(tmp_dir) / "clip.mp4")
        export_to_video(output, tmp_path, fps=_FPS)
        mp4_bytes = Path(tmp_path).read_bytes()

    return {
        "clip_base64": base64.b64encode(mp4_bytes).decode("ascii"),
        "duration_seconds": num_frames / _FPS,
        "width": _WIDTH,
        "height": _HEIGHT,
    }


runpod.serverless.start({"handler": handler})
