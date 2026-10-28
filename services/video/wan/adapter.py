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

import base64
import time

import httpx

from services.common.errors import ApprovalRequiredError, CostWarning
from services.video.engine import ClipJobLost, SceneClipRequest, SceneClipResult, VideoEngine

_RUNPOD_BASE_URL = "https://api.runpod.ai/v2"
_SUBMIT_TIMEOUT_SECONDS = 30
_POLL_INTERVAL_SECONDS = 5
# A 5-30s clip takes ~17 min on an RTX A4500 (50 steps at ~20s each), so the
# old 600s limit gave up on jobs that were still healthy. Keep this above the
# endpoint's execution timeout (1800s).
_POLL_TIMEOUT_SECONDS = 1800
_TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}


class WanEngine(VideoEngine):
    def __init__(self, runpod_api_key: str, wan_endpoint_id: str):
        self._runpod_api_key = runpod_api_key
        self._wan_endpoint_id = wan_endpoint_id

    def generate_clip(
        self,
        request: SceneClipRequest,
        output_path: str,
        on_submitted=None,
        resume_job_id: str | None = None,
    ) -> SceneClipResult:
        """Submit one clip and wait for it, or resume a job already on Runpod.

        on_submitted(job_id) runs the moment the job is accepted, so the caller
        can save the id before waiting. resume_job_id polls an existing job
        instead of submitting a new one (that job is already paid for).
        """
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
        if resume_job_id:
            job_id = resume_job_id
        else:
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
            if on_submitted is not None:
                on_submitted(job_id)

        output = self._wait_for_job(job_id, headers)
        # The worker returns the MP4 inline as base64 (handler.py),
        # so no storage keys are needed on the Runpod side.
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(output["clip_base64"]))

        return SceneClipResult(
            clip_path=output_path,
            duration_seconds=output.get("duration_seconds", request.duration_seconds),
        )

    def _wait_for_job(self, job_id: str, headers: dict) -> dict:
        """Poll until the job finishes and return its output. Raises ClipJobLost
        when Runpod no longer has a usable result, so the caller knows a fresh
        submission is safe; RuntimeError/TimeoutError otherwise."""
        deadline = time.monotonic() + _POLL_TIMEOUT_SECONDS
        while True:
            status_response = httpx.get(
                f"{_RUNPOD_BASE_URL}/{self._wan_endpoint_id}/status/{job_id}",
                headers=headers,
                timeout=_SUBMIT_TIMEOUT_SECONDS,
            )
            if status_response.status_code == 404:
                raise ClipJobLost(
                    f"Runpod no longer has job {job_id} (its result may have expired)"
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
            # Runpod puts the handler's traceback/crash reason at the top level
            # of the status payload (`error`) when a job ends FAILED/CANCELLED/
            # TIMED_OUT — `output` is null in that case. Surface it; without
            # this, every failure looked identical ("ended with status
            # 'FAILED'") with no way to tell OOM from a bad image pull from a
            # bug in handler.py short of opening the Runpod dashboard by hand.
            detail = payload.get("error")
            suffix = (
                f": {detail}"
                if detail
                else " (no error detail returned by Runpod — check the "
                "endpoint's own logs in the Runpod dashboard)"
            )
            raise ClipJobLost(f"Runpod job {job_id} ended with status '{status}'{suffix}")
        output = payload["output"]
        if "error" in output:
            raise ClipJobLost(f"Wan worker error for job {job_id}: {output['error']}")
        return output
