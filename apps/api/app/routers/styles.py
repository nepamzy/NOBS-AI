from fastapi import APIRouter

from app.schemas.style import StylePresetRead
from services.video.style_catalog import STYLE_PRESETS

router = APIRouter(prefix="/styles", tags=["styles"])


@router.get("", response_model=list[StylePresetRead])
def list_styles() -> list[StylePresetRead]:
    return [
        StylePresetRead(id=p.id, name=p.name, description=p.description, accent_hex=p.accent_hex)
        for p in STYLE_PRESETS
    ]
