import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_or_create_single_user(db: Session) -> User:
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


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    owner = _get_or_create_single_user(db)
    project = Project(owner_id=owner.id, name=payload.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
