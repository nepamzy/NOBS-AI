import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import PipelineStage
from app.storage import to_url


class VideoCreate(BaseModel):
    project_id: uuid.UUID
    topic: str
    target_duration_seconds: int
    voice_preset: str = ""
    style_preset: str = ""
    # Step 1 toggles (CLAUDE.md Part 3): let NOBS AI research vs. bring your own.
    run_research: bool = True


class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    topic: str
    target_duration_seconds: int
    voice_preset: str
    style_preset: str
    stage: PipelineStage
    stage_progress_percent: int
    stage_detail: str
    storyboard_approved: bool
    final_video_path: str | None
    auto_publish: bool
    youtube_video_id: str | None
    youtube_published: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def final_video_url(self) -> str | None:
        return to_url(self.final_video_path)


class ClipRecoverRequest(BaseModel):
    """The Runpod request id of a clip that was billed but never saved
    (copied from the Runpod Requests page). Ids are opaque tokens, not secrets."""

    runpod_job_id: str = Field(min_length=4, max_length=200, pattern=r"^[A-Za-z0-9_-]+$")
