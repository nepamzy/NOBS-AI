# Runpod Serverless worker: Wan2.1 T2V 1.3B. Built by Runpod from this repo.
# Built and running for real since Oct 2026; see handler.py's module
# docstring for the CUDA-OOM fix history on real paid runs.
FROM pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime

# Addresses the "N GiB reserved/unallocated" fragmentation pattern in the
# OOM traces from real runs — PyTorch's own documented fix for it. _pipe is
# a warm-worker singleton reused across many jobs, so fragmentation that
# would be harmless in a single short-lived process accumulates instead.
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-wan-worker.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Bake the model weights into the image so cold starts don't download ~5GB.
RUN python -c "from diffusers import AutoencoderKLWan, WanPipeline; \
import torch; \
m='Wan-AI/Wan2.1-T2V-1.3B-Diffusers'; \
AutoencoderKLWan.from_pretrained(m, subfolder='vae', torch_dtype=torch.float32); \
WanPipeline.from_pretrained(m, torch_dtype=torch.bfloat16)"

COPY handler.py /app/handler.py

CMD ["python", "-u", "/app/handler.py"]
