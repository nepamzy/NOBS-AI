import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.upload_schedule import UploadSchedule
from app.models.user import User
from app.routers.videos import _owned_project_or_404
from app.schemas.upload_schedule import UploadScheduleCreate, UploadScheduleRead

router = APIRouter(prefix="/upload-schedules", tags=["upload-schedules"])


def _owned_schedule_or_404(db: Session, schedule_id: uuid.UUID, user: User) -> UploadSchedule:
    from app.models.project import Project

    schedule = (
        db.query(UploadSchedule)
        .join(Project, Project.id == UploadSchedule.project_id)
        .filter(UploadSchedule.id == schedule_id, Project.owner_id == user.id)
        .one_or_none()
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("", response_model=UploadScheduleRead, status_code=201)
def create_schedule(
    payload: UploadScheduleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadSchedule:
    _owned_project_or_404(db, payload.project_id, user)

    schedule = UploadSchedule(**payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("", response_model=list[UploadScheduleRead])
def list_schedules(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[UploadSchedule]:
    from app.models.project import Project

    return (
        db.query(UploadSchedule)
        .join(Project, Project.id == UploadSchedule.project_id)
        .filter(Project.owner_id == user.id)
        .order_by(UploadSchedule.day_of_week, UploadSchedule.trigger_time)
        .all()
    )


@router.patch("/{schedule_id}", response_model=UploadScheduleRead)
def set_schedule_enabled(
    schedule_id: uuid.UUID,
    enabled: bool,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadSchedule:
    schedule = _owned_schedule_or_404(db, schedule_id, user)
    schedule.enabled = enabled
    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    schedule = _owned_schedule_or_404(db, schedule_id, user)
    db.delete(schedule)
    db.commit()
