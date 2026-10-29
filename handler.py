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
`torch.OutOfMemoryError`, first inside the transformer's attention block
("19.54 GiB already in use ... 30.00 MiB free"), then — after a first fix
attempt — inside the VAE's decode step ("18.87 GiB already in use ... 712 MiB
free, needed 884 MiB"). Not a code bug, a genuine peak-memory ceiling: this
worker only has ~19.6GB total, and loading the text encoder, transformer, and
VAE onto the GPU simultaneously (the original `.to("cuda")`) leaves too little
headroom.

The first fix attempt (attention slicing + VAE tiling/slicing) helped only a
little — confirmed by reading diffusers' own pinned-version source
(requirements-wan-worker.txt pins diffusers==0.33.1): `AutoencoderKLWan` at
that version has NO `enable_tiling`/`enable_slicing` and no tiling branch in
`_decode` at all, so those two calls were silent no-ops the whole time
(caught by their own defensive try/except). Attention slicing alone bought a
little headroom (the crash moved later, into VAE decode) but not enough.

Real fix: `WanPipeline` declares `model_cpu_offload_seq =
"text_encoder->transformer->vae"` (diffusers' own marker that this pipeline
supports CPU offload — confirmed against the pinned version's source, not
guessed), so `enable_model_cpu_offload()` keeps only the actively-running
component resident on the GPU instead of all three at once, addressing an OOM
regardless of which stage it happens in. Replaces the plain `.to("cuda")`
(the two are mutually exclusive — offload handles device placement itself).
`accelerate` (its dependency) was already in requirements-wan-worker.txt.
Real cost: slower per job (PCIe transfer between CPU/GPU per stage), on top
of the already-long generation time — acceptable against the alternative of
a bigger, pricier GPU tier. `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`
(Dockerfile) and the cache clear below still apply on top of this.
Still unverified against a real successful GPU run.
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
    """Lowers peak VRAM per job. enable_model_cpu_offload() is the real fix
    (see module docstring) — WanPipeline declares model_cpu_offload_seq, so
    this is confirmed-supported, not a guess. Attention slicing is kept as a
    cheap defensive extra on top. Each call is still wrapped individually:
    a diffusers/model version that doesn't support one must not crash job
    submission over it."""
    try:
        pipe.enable_attention_slicing()
    except Exception:
        pass
    pipe.enable_model_cpu_offload()


def _load_pipeline() -> WanPipeline:
    """Loaded once per worker, on the first job, then reused for later jobs.
    No .to("cuda") here — enable_model_cpu_offload() (below) places each
    component on the GPU only while it's actively running, which is the
    opposite of (and mutually exclusive with) moving the whole pipeline to
    the GPU up front."""
    global _pipe
    if _pipe is None:
        vae = AutoencoderKLWan.from_pretrained(_MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
        _pipe = WanPipeline.from_pretrained(_MODEL_ID, vae=vae, torch_dtype=torch.bfloat16)
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
