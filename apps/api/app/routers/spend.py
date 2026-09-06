from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.db import get_db
from app.models.cost_entry import CostEntry
from app.models.user import User
from app.schemas.cost_entry import CostEntryCreate, CostEntryRead, SpendSummary

router = APIRouter(prefix="/spend", tags=["spend"])


@router.get("", response_model=SpendSummary)
def list_spend(
    db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> SpendSummary:
    entries = db.query(CostEntry).order_by(CostEntry.occurred_at.desc()).all()
    return SpendSummary(
        entries=entries,
        total_estimated_usd=sum(e.estimated_cost_usd or 0 for e in entries),
        total_actual_usd=sum(e.actual_cost_usd or 0 for e in entries),
    )


@router.post("", response_model=CostEntryRead, status_code=201)
def create_spend_entry(
    payload: CostEntryCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> CostEntry:
    entry = CostEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
