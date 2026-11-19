import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# A loose shape check, not full RFC validation — this is a free-text
# contact capture, not an auth flow, and pydantic's EmailStr would pull in
# a new dependency (email-validator) just for this one field.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class WaitlistSignupCreate(BaseModel):
    email: str = Field(max_length=320, pattern=_EMAIL_PATTERN)
    name: str = Field(default="", max_length=200)

    # Browsers/phones paste trailing spaces and some clients send null for an
    # empty field — tidy both BEFORE the shape check so a real visitor is
    # never bounced with a 422 over whitespace.
    @field_validator("email", mode="before")
    @classmethod
    def _tidy_email(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("name", mode="before")
    @classmethod
    def _tidy_name(cls, value: object) -> object:
        if value is None:
            return ""
        return value.strip() if isinstance(value, str) else value


class WaitlistSignupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    source: str
    youtube_channel_title: str | None
    created_at: datetime
