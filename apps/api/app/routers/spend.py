import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.db import get_db
from app.models.cost_entry import CostEntry
from app.models.enums import BillingType, CostStatus
from app.models.user import User
from app.schemas.cost_entry import (
    CategoryBreakdown,
    CostEntryCreate,
    CostEntryRead,
    CostEntryUpdate,
    SpendSummary,
)

router = APIRouter(prefix="/spend", tags=["spend"])


def _build_summary(entries: list[CostEntry]) -> SpendSummary:
    by_category: dict[str, CategoryBreakdown] = {}
    for entry in entries:
        bucket = by_category.setdefault(
            entry.category,
            CategoryBreakdown(category=entry.category, estimated_usd=0, actual_usd=0),
        )
        bucket.estimated_usd += entry.estimated_cost_usd or 0
        bucket.actual_usd += entry.actual_cost_usd or 0

    def _monthly_cost(entry: CostEntry) -> float:
        return (
            entry.actual_cost_usd if entry.actual_cost_usd is not None else entry.estimated_cost_usd
        ) or 0

    active_monthly_recurring = sum(
        _monthly_cost(entry)
        for entry in entries
        if entry.status == CostStatus.ACTIVE and entry.billing_type == BillingType.MONTHLY
    )

    return SpendSummary(
        entries=entries,
        total_estimated_usd=sum(e.estimated_cost_usd or 0 for e in entries),
        total_actual_usd=sum(e.actual_cost_usd or 0 for e in entries),
        active_monthly_recurring_usd=active_monthly_recurring,
        pending_count=sum(1 for e in entries if e.status == CostStatus.PENDING),
        active_count=sum(1 for e in entries if e.status == CostStatus.ACTIVE),
        by_category=list(by_category.values()),
    )


@router.get("", response_model=SpendSummary)
def list_spend(
    db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> SpendSummary:
    entries = db.query(CostEntry).order_by(CostEntry.occurred_at.desc()).all()
    return _build_summary(entries)


@router.post("", response_model=CostEntryRead, status_code=201)
def create_spend_entry(
    payload: CostEntryCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> CostEntry:
    entry = CostEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=CostEntryRead)
def update_spend_entry(
    entry_id: uuid.UUID,
    payload: CostEntryUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> CostEntry:
    entry = db.get(CostEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Cost entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_spend_entry(
    entry_id: uuid.UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> None:
    entry = db.get(CostEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Cost entry not found")
    db.delete(entry)
    db.commit()
