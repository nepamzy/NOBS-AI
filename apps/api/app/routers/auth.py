from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import (
    generate_session_token,
    hash_lookup_value,
    hash_password,
    verify_password,
)
from app.db import get_db
from app.models.auth import AuthSession, SignupPin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    SignupRequest,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_LIFETIME = timedelta(days=30)


def _create_session(db: Session, user: User) -> str:
    token = generate_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_lookup_value(token),
            expires_at=datetime.now(UTC) + SESSION_LIFETIME,
        )
    )
    db.commit()
    return token


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    pin = (
        db.query(SignupPin)
        .filter(SignupPin.code_hash == hash_lookup_value(payload.pin_code))
        .one_or_none()
    )
    if pin is None or pin.used or pin.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="PIN is invalid, used, or expired")

    if db.query(User).filter(User.email == payload.email).one_or_none() is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    db.flush()  # assigns user.id without committing yet

    # A PIN allows exactly one signup, ever — marking it used here, in the
    # same transaction as creating the account, is what makes it single-use
    # rather than a race between two people submitting it at once.
    pin.used = True
    pin.used_by_user_id = user.id
    db.commit()
    db.refresh(user)

    token = _create_session(db, user)
    return AuthResponse(token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended")

    token = _create_session(db, user)
    return AuthResponse(token=token, user=UserRead.model_validate(user))


@router.post("/logout", status_code=204)
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),  # ensures the token is valid before deleting it
) -> None:
    token = (authorization or "").removeprefix("Bearer ").strip()
    db.query(AuthSession).filter(AuthSession.token_hash == hash_lookup_value(token)).delete()
    db.commit()


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.put("/password", response_model=UserRead)
def change_password(
    payload: ChangePasswordRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserRead:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)

    # A password change is a "something may be compromised" moment — sign
    # out every other session, keeping only the one making this request, so
    # changing the password actually locks other access out immediately.
    current_token = (authorization or "").removeprefix("Bearer ").strip()
    db.query(AuthSession).filter(
        AuthSession.user_id == user.id,
        AuthSession.token_hash != hash_lookup_value(current_token),
    ).delete()

    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)
