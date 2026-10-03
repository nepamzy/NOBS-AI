import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VideoFeedbackCreate(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class VideoFeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    note: str
    created_at: datetime
