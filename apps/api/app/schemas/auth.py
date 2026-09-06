import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import UserRole

# Deliberately simple (no email-validator dependency) — just enough to
# reject obviously-malformed input; the DB's unique constraint on email is
# the real integrity guarantee.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    if not _EMAIL_PATTERN.match(value):
        raise ValueError("Not a valid email address")
    return value.lower()


class SignupRequest(BaseModel):
    pin_code: str
    email: str
    password: str
    display_name: str

    _validate = field_validator("email")(_validate_email)


class LoginRequest(BaseModel):
    email: str
    password: str

    _validate = field_validator("email")(_validate_email)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    is_suspended: bool
    token_balance: int
    created_at: datetime


class AuthResponse(BaseModel):
    token: str
    user: UserRead


class SignupPinRead(BaseModel):
    """The plaintext code — returned ONLY here, at generation time. It's
    never stored or retrievable again after this response."""

    code: str
    expires_at: datetime
