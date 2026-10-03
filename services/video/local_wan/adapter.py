"""Local Wan adapter — talks to a Wan 2.1 inference server Nobert runs
himself on his own GPU (see scripts/local_wan_server.py and
LOCAL_WAN_SETUP.md), instead of renting one on Runpod.

Replaces the earlier, unreviewed Vast.ai adapter (deleted, not fixed — it
had no cost-approval gate before auto-renting a GPU, and a shell-injection
bug in how it passed the scene prompt to its generation container). This
is a better fit for Nobert's actual situation: he has a free 8GB-VRAM
laptop GPU, and Wan2.1-T2V-1.3B is specifically sized for 8GB cards (runs
480p clips in ~4-6 min each on an RTX 4060 8GB-class GPU) — zero
marginal cost beyond electricity, versus ~$1.39-2.89/hr for a rented one.

Trade-off, stated plainly: his laptop has to be on and running the local
server when a clip needs generating. No laptop running = generation stays
blocked (ApprovalRequiredError/EngineNotConfiguredError below), exactly
like any other not-yet-configured engine — the pipeline parks itself
rather than silently failing or falling back to a paid provider.

Same ApprovalRequiredError gating as every other engine here (see
Chatterbox for the same pattern on the voice side) — "local" doesn't mean
"skip the approval step," it means the likely cost is his own hardware,
not a bill. Nobert still has to point LOCAL_WAN_API_URL at a real,
running server before this does anything.
"""

import httpx

from services.common.errors import ApprovalRequiredError, CostWarning
from services.video.engine import SceneClipRequest, SceneClipResult, VideoEngine

_REQUEST_TIMEOUT_SECONDS = 900  # a 480p/5s clip takes several minutes on an 8GB GPU


class LocalWanEngine(VideoEngine):
    def __init__(self, api_url: str):
        self._api_url = api_url.rstrip("/") if api_url else ""

    def generate_clip(self, request: SceneClipRequest, output_path: str) -> SceneClipResult:
        if not self._api_url:
            raise ApprovalRequiredError(
                CostWarning(
                    action=f"Generate {request.duration_seconds}s clip for "
                    f"scene {request.scene_id} via local Wan",
                    service="Wan 2.1 1.3B, self-hosted on Nobert's own GPU",
                    expected_cost="Free (his own hardware/electricity) as "
                    "long as LOCAL_WAN_API_URL points at a server he's "
                    "already running — see LOCAL_WAN_SETUP.md",
                    billing_type="none (self-hosted) unless he later points "
                    "this at a rented GPU instead of his laptop",
                    max_expected_cost="$0 on his own laptop; unknown if "
                    "repointed at rented hardware",
                    risk="Low",
                    why_needed="No LOCAL_WAN_API_URL configured — the local "
                    "generation server must be started on his GPU first.",
                )
            )

        response = httpx.post(
            f"{self._api_url}/generate",
            json={
                "prompt": request.visual_prompt,
                "duration_seconds": request.duration_seconds,
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        actual_duration = response.headers.get("x-clip-duration-seconds")
        return SceneClipResult(
            clip_path=output_path,
            duration_seconds=float(actual_duration)
            if actual_duration
            else float(request.duration_seconds),
        )
