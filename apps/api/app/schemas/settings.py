from pydantic import BaseModel


class SettingsRead(BaseModel):
    default_duration_minutes: int
    default_voice_preset: str
    default_style_preset: str
    weekly_goal: int


class SettingsUpdate(BaseModel):
    default_duration_minutes: int | None = None
    default_voice_preset: str | None = None
    default_style_preset: str | None = None
    weekly_goal: int | None = None
