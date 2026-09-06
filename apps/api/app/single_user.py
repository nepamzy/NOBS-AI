from sqlalchemy.orm import Session

from app.models.user import User


def get_or_create_single_user(db: Session) -> User:
    """V1 is single-user (Nobert). Rather than build auth now, use one
    well-known local user row — swapping this for real auth later doesn't
    touch the schema (CLAUDE.md: multi-user is explicitly out of scope for V1)."""
    user = db.query(User).first()
    if user is None:
        user = User(email="nobert@local", display_name="Nobert")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
