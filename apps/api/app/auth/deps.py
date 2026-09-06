from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import hash_lookup_value
from app.db import get_db
from app.models.auth import AuthSession
from app.models.enums import UserRole
from app.models.user import User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()

    session = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == hash_lookup_value(token))
        .one_or_none()
    )
    if session is None or session.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    # Re-checked on every request, not just at login, so a suspension takes
    # effect immediately even for sessions already issued.
    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended")

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
