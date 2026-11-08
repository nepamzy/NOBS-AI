import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# A loose shape check, not full RFC validation — this is a free-text
# contact capture, not an auth flow, and pydantic's EmailStr would pull in
# a new dependency (email-validator) just for this one field.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class WaitlistSignupCreate(BaseModel):
    email: str = Field(max_length=320, pattern=_EMAIL_PATTERN)
    name: str = Field(default="", max_length=200)


class WaitlistSignupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
