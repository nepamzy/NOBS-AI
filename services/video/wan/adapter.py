"""Wan adapter, running behind a Runpod Serverless endpoint (CLAUDE.md
Part 3 - GPU infrastructure):

    NOBS AI SERVER -> request GPU -> RUNPOD -> GPU WORKER -> WAN
        -> generated clips -> Object Storage

Serverless (not a persistent Pod) is deliberate: Runpod bills per second of
active worker time and scales to zero between jobs, so there is no idle
cost between video generations — matching CLAUDE.md's "pay only when used"
requirement. A persistent Pod would keep billing while sitting idle.

Every call here would provision paid GPU time, so it always raises
ApprovalRequiredError until Nobert has approved that specific spend and
RUNPOD_API_KEY / WAN_ENDPOINT_ID are configured.

The exact `input` payload shape (prompt/duration/... field names) is
determined by whichever Wan worker template Nobert deploys on Runpod — the
fields below (prompt, duration_seconds) are a reasonable starting guess,
not a verified contract. Confirm/adjust against the specific template's
documented input schema before the first real run.
"""

import time

import httpx

from services.common.errors import ApprovalRequiredError, CostWarning
from services.video.engine import SceneClipRequest, SceneClipResult, VideoEngine

_RUNPOD_BASE_URL = "https://api.runpod.ai/v2"
_SUBMIT_TIMEOUT_SECONDS = 30
_POLL_INTERVAL_SECONDS = 5
_POLL_TIMEOUT_SECONDS = 600  # a single short clip should never take this long
_TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}


class WanEngine(VideoEngine):
    def __init__(self, runpod_api_key: str, wan_endpoint_id: str):
        self._runpod_api_key = runpod_api_key
        self._wan_endpoint_id = wan_endpoint_id

    def generate_clip(self, request: SceneClipRequest, output_path: str) -> SceneClipResult:
        if not self._runpod_api_key or not self._wan_endpoint_id:
            raise ApprovalRequiredError(
                CostWarning(
                    action=f"Generate {request.duration_seconds}s clip for "
                    f"scene {request.scene_id} via Wan",
                    service="Runpod Serverless GPU (Wan endpoint)",
                    expected_cost="~$2.72/hr equivalent for an A100 "
                    "(CLAUDE.md Part 4 estimate, re-verify current pricing) "
                    "billed per second of active generation time only",
                    billing_type="usage-based (per-second, scales to zero "
                    "when idle)",
                    max_expected_cost="Depends on generation time per clip "
                    "— unmeasured; test with a single short clip first",
                    risk="Medium",
                    why_needed="No RUNPOD_API_KEY/WAN_ENDPOINT_ID configured "
                    "— provisioning GPU time is a paid, approval-required "
                    "action.",
                )
            )
        headers = {
            "Authorization": f"Bearer {self._runpod_api_key}",
            "Content-Type": "application/json",
        }
        submit_response = httpx.post(
            f"{_RUNPOD_BASE_URL}/{self._wan_endpoint_id}/run",
            headers=headers,
            json={
                "input": {
                    "prompt": request.visual_prompt,
                    "duration_seconds": request.duration_seconds,
                }
            },
            timeout=_SUBMIT_TIMEOUT_SECONDS,
        )
        submit_response.raise_for_status()
        job_id = submit_response.json()["id"]

        deadline = time.monotonic() + _POLL_TIMEOUT_SECONDS
        while True:
            status_response = httpx.get(
                f"{_RUNPOD_BASE_URL}/{self._wan_endpoint_id}/status/{job_id}",
                headers=headers,
                timeout=_SUBMIT_TIMEOUT_SECONDS,
            )
            status_response.raise_for_status()
            payload = status_response.json()
            status = payload["status"]
            if status in _TERMINAL_STATUSES:
                break
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Runpod job {job_id} still '{status}' after "
                    f"{_POLL_TIMEOUT_SECONDS}s — see Runpod dashboard"
                )
            time.sleep(_POLL_INTERVAL_SECONDS)

        if status != "COMPLETED":
            raise RuntimeError(f"Runpod job {job_id} ended with status '{status}': {payload}")

        output = payload["output"]
        clip_url = output["clip_url"]
        clip_response = httpx.get(clip_url, timeout=_SUBMIT_TIMEOUT_SECONDS)
        clip_response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(clip_response.content)

        return SceneClipResult(
            clip_path=output_path,
            duration_seconds=output.get("duration_seconds", request.duration_seconds),
        )
