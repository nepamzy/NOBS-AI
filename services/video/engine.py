"""Video engine abstraction (CLAUDE.md Part 3):

    NOBS AI -> VIDEO ENGINE -> Wan

so Runway/Kling/Luma/Veo/Pika can be added later without rebuilding the app.
Generates one short clip (5-12s) per scene, never one long render.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SceneClipRequest:
    scene_id: str
    visual_prompt: str
    duration_seconds: int


@dataclass
class SceneClipResult:
    clip_path: str
    duration_seconds: float


class ClipJobLost(RuntimeError):
    """A remote clip job can no longer be retrieved (expired, cancelled, or failed
    on the provider). The caller may safely submit a new one."""


class VideoEngine(ABC):
    @abstractmethod
    def generate_clip(
        self,
        request: SceneClipRequest,
        output_path: str,
        on_submitted=None,
        resume_job_id: str | None = None,
    ) -> SceneClipResult: ...
