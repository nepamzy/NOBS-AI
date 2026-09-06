from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.models.user_setting import UserSetting
from app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

# CLAUDE.md Part 4's cost baseline is built around ~3 videos/week; that's
# also Dashboard's default weekly goal until changed here.
_DEFAULTS = {
    "default_duration_minutes": "3",
    "default_voice_preset": "",
    "default_style_preset": "",
    "weekly_goal": "3",
}


def _load_values(db: Session, user_id) -> dict[str, str]:
    rows = db.query(UserSetting).filter(UserSetting.user_id == user_id).all()
    values = dict(_DEFAULTS)
    for row in rows:
        if row.key in values:
            values[row.key] = row.value
    return values


def _to_read(values: dict[str, str]) -> SettingsRead:
    return SettingsRead(
        default_duration_minutes=int(values["default_duration_minutes"]),
        default_voice_preset=values["default_voice_preset"],
        default_style_preset=values["default_style_preset"],
        weekly_goal=int(values["weekly_goal"]),
    )


@router.get("", response_model=SettingsRead)
def get_settings(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SettingsRead:
    return _to_read(_load_values(db, user.id))


@router.put("", response_model=SettingsRead)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingsRead:
    updates = payload.model_dump(exclude_unset=True)

    for key, value in updates.items():
        row = (
            db.query(UserSetting)
            .filter(UserSetting.user_id == user.id, UserSetting.key == key)
            .one_or_none()
        )
        if row is None:
            db.add(UserSetting(user_id=user.id, key=key, value=str(value)))
        else:
            row.value = str(value)
    db.commit()

    return _to_read(_load_values(db, user.id))
