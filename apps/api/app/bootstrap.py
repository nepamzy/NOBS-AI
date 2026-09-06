"""Creates the one ADMIN account on first startup, from ADMIN_EMAIL /
ADMIN_PASSWORD (.env) — there's no signup form for the admin (a PIN-gated
signup needs an admin to issue the PIN, so the first account can't come
from that flow). Only runs when no ADMIN user exists yet; safe to call on
every startup after that.
"""

import logging

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import settings
from app.models.enums import UserRole
from app.models.user import User

logger = logging.getLogger(__name__)


def ensure_admin_exists(db: Session) -> None:
    if db.query(User).filter(User.role == UserRole.ADMIN).first() is not None:
        return

    if not settings.admin_email or not settings.admin_password:
        logger.warning(
            "No ADMIN user exists and ADMIN_EMAIL/ADMIN_PASSWORD are not set in "
            ".env — signup/login/admin routes will have no admin account to use. "
            "Set both and restart."
        )
        return

    db.add(
        User(
            email=settings.admin_email,
            display_name="Nobert",
            password_hash=hash_password(settings.admin_password),
            role=UserRole.ADMIN,
        )
    )
    db.commit()
    logger.info("Bootstrapped ADMIN account for %s", settings.admin_email)
