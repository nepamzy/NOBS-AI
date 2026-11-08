from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.db import get_db
from app.models.user import User
from app.models.waitlist_signup import WaitlistSignup
from app.schemas.waitlist import WaitlistSignupCreate, WaitlistSignupRead

router = APIRouter(tags=["waitlist"])


@router.post("/waitlist", response_model=WaitlistSignupRead, status_code=201)
def join_waitlist(payload: WaitlistSignupCreate, db: Session = Depends(get_db)) -> WaitlistSignup:
    """Public, unauthenticated — the landing page's waitlist form (no
    account, no sign-up, per CLAUDE.md Part 2: V1 is single-user, this is
    just capturing contacts for whenever it opens up beyond that).
    Re-submitting the same email is treated as success, not an error —
    nothing about this should ever feel like a login/signup flow."""
    email = payload.email.strip().lower()
    existing = db.query(WaitlistSignup).filter(WaitlistSignup.email == email).one_or_none()
    if existing is not None:
        return existing

    signup = WaitlistSignup(email=email, name=payload.name.strip())
    db.add(signup)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race with a concurrent signup for the same email — treat
        # it the same as the one_or_none() hit above.
        db.rollback()
        return db.query(WaitlistSignup).filter(WaitlistSignup.email == email).one()
    db.refresh(signup)
    return signup


@router.get("/admin/waitlist", response_model=list[WaitlistSignupRead])
def list_waitlist(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> list[WaitlistSignup]:
    return db.query(WaitlistSignup).order_by(WaitlistSignup.created_at.desc()).all()
