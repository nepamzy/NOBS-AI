import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Project]:
    return (
        db.query(Project)
        .filter(Project.owner_id == user.id)
        .order_by(Project.created_at.desc())
        .all()
    )


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Project:
    project = Project(owner_id=user.id, name=payload.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Project:
    project = db.get(Project, project_id)
    # 404, not 403, when it's not theirs — don't confirm another user's
    # project id even exists.
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
