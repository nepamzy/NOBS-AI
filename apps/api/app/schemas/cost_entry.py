import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CostCategory


class CostEntryCreate(BaseModel):
    category: CostCategory
    service: str
    purpose: str
    video_id: uuid.UUID | None = None
    estimated_cost_usd: float | None = None
    actual_cost_usd: float | None = None


class CostEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: CostCategory
    service: str
    purpose: str
    video_id: uuid.UUID | None
    estimated_cost_usd: float | None
    actual_cost_usd: float | None
    occurred_at: datetime


class SpendSummary(BaseModel):
    entries: list[CostEntryRead]
    total_estimated_usd: float
    total_actual_usd: float
