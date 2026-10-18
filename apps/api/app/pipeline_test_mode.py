"""Admin-wide TEST MODE switch for the video pipeline.

When on, the pipeline skips narration, audio mixing, music and captions, so a
silent video can be reviewed. It is for testing only and affects every new
video while it is on.

Storage: one row in the existing `settings` table, on the admin user, key
"pipeline_test_no_audio". The worker has no user context, so the admin's row
is the single source of truth. If no row exists, the env var
PIPELINE_TEST_NO_AUDIO (default false) decides.
"""

from sqlalchemy.orm import Session

from app.config import settings
from app.models.enums import UserRole
from app.models.user import User
from app.models.user_setting import UserSetting

KEY = "pipeline_test_no_audio"


def _admin(db: Session) -> User | None:
    return db.query(User).filter(User.role == UserRole.ADMIN).first()


def get_enabled(db: Session) -> bool:
    admin = _admin(db)
    if admin is None:
        return settings.pipeline_test_no_audio
    row = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == admin.id, UserSetting.key == KEY)
        .one_or_none()
    )
    if row is None:
        return settings.pipeline_test_no_audio
    return row.value == "true"


def set_enabled(db: Session, enabled: bool) -> bool:
    admin = _admin(db)
    if admin is None:
        raise RuntimeError("No admin user exists to store the test-mode flag on")
    row = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == admin.id, UserSetting.key == KEY)
        .one_or_none()
    )
    value = "true" if enabled else "false"
    if row is None:
        db.add(UserSetting(user_id=admin.id, key=KEY, value=value))
    else:
        row.value = value
    db.commit()
    return enabled
