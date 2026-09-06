import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.auth.security import generate_pin_code, hash_lookup_value
from app.db import get_db
from app.models.auth import AuthSession, SignupPin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import SignupPinRead, UserRead

router = APIRouter(prefix="/admin", tags=["admin"])

PIN_LIFETIME = timedelta(minutes=5)


@router.post("/pins", response_model=SignupPinRead, status_code=201)
def generate_pin(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> SignupPinRead:
    code = generate_pin_code()
    expires_at = datetime.now(UTC) + PIN_LIFETIME
    db.add(
        SignupPin(
            code_hash=hash_lookup_value(code),
            expires_at=expires_at,
            created_by_user_id=admin.id,
        )
    )
    db.commit()
    # The only moment the plaintext code exists anywhere — send it to
    # whoever you're inviting yourself; it can't be retrieved again.
    return SignupPinRead(code=code, expires_at=expires_at)


@router.get("/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> list[User]:
    return db.query(User).filter(User.role == UserRole.USER).order_by(User.created_at.desc()).all()


@router.post("/users/{user_id}/suspend", response_model=UserRead)
def suspend_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> User:
    user = _get_manageable_user(db, user_id)
    user.is_suspended = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/unsuspend", response_model=UserRead)
def unsuspend_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> User:
    user = _get_manageable_user(db, user_id)
    user.is_suspended = False
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> None:
    user = _get_manageable_user(db, user_id)
    # Not covered by the User.projects/.settings ORM cascade below: sessions
    # (no relationship declared) and any pin this user used (kept for audit
    # — just detached from the now-deleted account, not deleted itself).
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.query(SignupPin).filter(SignupPin.used_by_user_id == user.id).update(
        {"used_by_user_id": None}
    )
    db.delete(user)  # cascades to their projects/videos/settings (see User model)
    db.commit()


class GrantTokensRequest(BaseModel):
    amount: int


@router.post("/users/{user_id}/grant-tokens", response_model=UserRead)
def grant_tokens(
    user_id: uuid.UUID,
    payload: GrantTokensRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> User:
    """Standing in for real payment (not built yet — see chat history):
    admin manually tops up a user's balance until a payment processor is
    designed and approved."""
    user = _get_manageable_user(db, user_id)
    user.token_balance += payload.amount
    db.commit()
    db.refresh(user)
    return user


def _get_manageable_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None or user.role == UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="User not found")
    return user
