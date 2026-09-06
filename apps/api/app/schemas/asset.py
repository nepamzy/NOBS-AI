import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.enums import AssetType
from app.storage import to_url


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    asset_type: AssetType
    path: str
    label: str
    created_at: datetime

    @computed_field
    @property
    def url(self) -> str | None:
        return to_url(self.path)
