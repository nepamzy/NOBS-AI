"""Wan adapter, running behind Runpod (CLAUDE.md Part 3 - GPU infrastructure):

    NOBS AI SERVER -> request GPU -> RUNPOD -> GPU WORKER -> WAN
        -> generated clips -> Object Storage

Every call here would provision paid GPU time, so it always raises
ApprovalRequiredError until Nobert has approved that specific spend and
RUNPOD_API_KEY / WAN_ENDPOINT_ID are configured.
"""

from services.common.errors import ApprovalRequiredError, CostWarning
from services.video.engine import SceneClipRequest, SceneClipResult, VideoEngine


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
                    service="Runpod GPU (Wan endpoint)",
                    expected_cost="~$1.19-1.99/hr for an A100 80GB pod "
                    "(CLAUDE.md Part 4 estimate, re-verify current pricing)",
                    billing_type="hourly (per-second billing while pod is up)",
                    max_expected_cost="Depends on generation time per clip; "
                    "test with a single short clip first",
                    risk="Medium",
                    why_needed="No RUNPOD_API_KEY/WAN_ENDPOINT_ID configured "
                    "— provisioning a GPU pod is a paid, approval-required "
                    "action.",
                )
            )
        # Real Runpod job submission + polling goes here.
        raise NotImplementedError("Runpod/Wan call not yet implemented")
