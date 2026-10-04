import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import BillingType, CostCategory, CostStatus


class CostEntryCreate(BaseModel):
    category: CostCategory
    service: str
    purpose: str
    status: CostStatus = CostStatus.ACTIVE
    billing_type: BillingType | None = None
    video_id: uuid.UUID | None = None
    estimated_cost_usd: float | None = None
    actual_cost_usd: float | None = None


class CostEntryUpdate(BaseModel):
    status: CostStatus | None = None
    billing_type: BillingType | None = None
    estimated_cost_usd: float | None = None
    actual_cost_usd: float | None = None


class CostEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: CostCategory
    service: str
    purpose: str
    status: CostStatus
    billing_type: BillingType | None
    video_id: uuid.UUID | None
    estimated_cost_usd: float | None
    actual_cost_usd: float | None
    occurred_at: datetime


class CategoryBreakdown(BaseModel):
    category: CostCategory
    estimated_usd: float
    actual_usd: float


class SpendSummary(BaseModel):
    entries: list[CostEntryRead]
    total_estimated_usd: float
    total_actual_usd: float
    active_monthly_recurring_usd: float
    pending_count: int
    active_count: int
    by_category: list[CategoryBreakdown]
