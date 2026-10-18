# Runpod Serverless worker: Wan2.1 T2V 1.3B. Built by Runpod from this repo.
# NOT yet built or tested. The base image tag and package pins must be confirmed
# on the first real build; a wrong tag fails the build before any GPU time is billed.
FROM pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY runpod_wan_worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Bake the model weights into the image so cold starts don't download ~5GB.
RUN python -c "from diffusers import AutoencoderKLWan, WanPipeline; \
import torch; \
m='Wan-AI/Wan2.1-T2V-1.3B-Diffusers'; \
AutoencoderKLWan.from_pretrained(m, subfolder='vae', torch_dtype=torch.float32); \
WanPipeline.from_pretrained(m, torch_dtype=torch.bfloat16)"

COPY runpod_wan_worker/handler.py /app/handler.py

CMD ["python", "-u", "/app/handler.py"]
