import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import TransitionType


class SceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order: int
    narration: str
    visual_prompt: str
    duration_seconds: int
    transition: TransitionType


class SceneUpdate(BaseModel):
    narration: str | None = None
    visual_prompt: str | None = None
    duration_seconds: int | None = None
    transition: TransitionType | None = None


class ScriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    title: str
    hook: str
    estimated_duration_seconds: int
    word_count: int
    approved: bool
    scenes: list[SceneRead]
    created_at: datetime
    updated_at: datetime
