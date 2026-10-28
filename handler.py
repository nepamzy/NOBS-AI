"""Runpod Serverless worker for Wan 2.1 text-to-video (1.3B).

Deployed from this repo on Runpod (Serverless -> New Endpoint -> GitHub repo,
Dockerfile in repo root). Contract, matching services/video/wan/adapter.py:

    input:  {"prompt": str, "duration_seconds": int}
    output: {"clip_base64": str, "duration_seconds": float, "width": int, "height": int}

The clip comes back inside the response as base64 MP4, so this worker needs no
storage keys and no external bucket. A 5-second 480p clip is small enough for that.

Model: Wan-AI/Wan2.1-T2V-1.3B-Diffusers. The 1.3B checkpoint is chosen because it
fits in 16GB VRAM with room to spare (the 14B model is tight on 16GB). The weights
are downloaded at Docker build time (see Dockerfile) so a cold worker doesn't
spend billed GPU time downloading ~5GB.

The first real paid runs (Oct 2026, on a 19.58GB-VRAM worker) crashed with
`torch.OutOfMemoryError` ("19.54 GiB already in use ... 30.00 MiB free") inside
the transformer's attention block — not a code bug, a genuine peak-memory
ceiling, worsened by `_pipe` being a warm-worker singleton reused across many
jobs (CUDA allocator fragmentation accumulates job over job, per the "2.94 GiB
reserved/unallocated" in that same error). Fixed with attention slicing + VAE
tiling (lower peak memory per job, each a no-op if the installed diffusers
version doesn't support it on this model) and an explicit cache clear after
every job. `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (Dockerfile) is
the other half — PyTorch's own documented fix for that exact "reserved but
unallocated" fragmentation pattern. Still unverified against a real GPU run
since none has succeeded yet; if jobs still OOM after this, the next lever is
`enable_sequential_cpu_offload()` (slower, but far lower peak VRAM) before
reaching for a bigger/pricier GPU tier.
"""

import base64
import gc
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


def _enable_memory_savings(pipe: WanPipeline) -> None:
    """Lowers peak VRAM per job at some speed cost. Each call is wrapped
    individually and best-effort: a diffusers/model version that doesn't
    support a given method must not crash job submission over it."""
    try:
        pipe.enable_attention_slicing()
    except Exception:
        pass
    try:
        pipe.vae.enable_tiling()
    except Exception:
        pass
    try:
        pipe.vae.enable_slicing()
    except Exception:
        pass


def _load_pipeline() -> WanPipeline:
    """Loaded once per worker, on the first job, then reused for later jobs."""
    global _pipe
    if _pipe is None:
        vae = AutoencoderKLWan.from_pretrained(_MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
        _pipe = WanPipeline.from_pretrained(_MODEL_ID, vae=vae, torch_dtype=torch.bfloat16)
        _pipe.to("cuda")
        _enable_memory_savings(_pipe)
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
    try:
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
    finally:
        # _pipe is a warm-worker singleton reused across many jobs — without
        # this, allocator fragmentation (torch.cuda's "reserved but
        # unallocated" memory) builds up job over job until a later job OOMs
        # even though any one job alone would have fit. Runs on failure too.
        gc.collect()
        torch.cuda.empty_cache()

    return {
        "clip_base64": base64.b64encode(mp4_bytes).decode("ascii"),
        "duration_seconds": num_frames / _FPS,
        "width": _WIDTH,
        "height": _HEIGHT,
    }


runpod.serverless.start({"handler": handler})
