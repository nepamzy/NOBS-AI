"""Drives one VideoEngine call per scene. Kept separate from the adapters
(services/video/wan) so a future multi-provider fallback or parallel-clip
strategy lives here, not inside any one provider's adapter."""

from collections.abc import Iterable

from services.video.engine import SceneClipRequest, SceneClipResult, VideoEngine


def generate_scene_clips(
    engine: VideoEngine,
    requests: Iterable[SceneClipRequest],
    output_dir: str,
) -> dict[str, SceneClipResult]:
    """Generate one clip per scene. Stops at the first failure (including
    ApprovalRequiredError) rather than partially generating and hiding it —
    a bad/blocked scene should be visible, not silently skipped."""
    results: dict[str, SceneClipResult] = {}
    for req in requests:
        output_path = f"{output_dir}/{req.scene_id}.mp4"
        results[req.scene_id] = engine.generate_clip(req, output_path)
    return results
