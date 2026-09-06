from pydantic import BaseModel


class StylePresetRead(BaseModel):
    id: str
    name: str
    description: str
    accent_hex: str
