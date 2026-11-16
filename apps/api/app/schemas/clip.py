import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import ClipJobStage
from app.storage import to_url


class SourceVideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    stage: ClipJobStage
    stage_detail: str
    target_clip_count: int
    auto_publish: bool
    created_at: datetime
    updated_at: datetime
    source_path: str = Field(exclude=True)

    @computed_field
    @property
    def source_url(self) -> str | None:
        """The uploaded file, playable in the browser. None for clips Claude
        supplied, which have no source file in NOBS AI."""
        if self.source_path.startswith("external:"):
            return None
        return to_url(self.source_path)


class SourceVideoUpdate(BaseModel):
    auto_publish: bool | None = None


class ClipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_video_id: uuid.UUID
    start_seconds: float
    end_seconds: float
    title: str
    reason: str
    clip_path: str | None
    youtube_video_id: str | None
    youtube_channel: str | None
    format: str | None
    youtube_published: bool
    created_at: datetime

    @computed_field
    @property
    def clip_url(self) -> str | None:
        return to_url(self.clip_path)
