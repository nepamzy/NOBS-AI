import re
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class UploadScheduleCreate(BaseModel):
    project_id: uuid.UUID
    day_of_week: int  # 0=Monday .. 6=Sunday
    trigger_time: str  # "HH:MM", UTC
    topic: str
    target_duration_seconds: int
    voice_preset: str = ""
    style_preset: str = ""
    run_research: bool = True
    # Defaults False always — see app/models/upload_schedule.py.
    auto_publish: bool = False

    @field_validator("day_of_week")
    @classmethod
    def _validate_day(cls, v: int) -> int:
        if not (0 <= v <= 6):
            raise ValueError("day_of_week must be 0 (Monday) through 6 (Sunday)")
        return v

    @field_validator("trigger_time")
    @classmethod
    def _validate_time(cls, v: str) -> str:
        if not _TIME_RE.match(v):
            raise ValueError("trigger_time must be 'HH:MM' 24-hour UTC")
        return v


class UploadScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    day_of_week: int
    trigger_time: str
    topic: str
    target_duration_seconds: int
    voice_preset: str
    style_preset: str
    run_research: bool
    enabled: bool
    auto_publish: bool


class UploadScheduleUpdate(BaseModel):
    """PATCH body — only the fields actually sent are changed."""

    enabled: bool | None = None
    auto_publish: bool | None = None
