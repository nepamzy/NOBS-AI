import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

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
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def final_video_url(self) -> str | None:
        return to_url(self.final_video_path)
