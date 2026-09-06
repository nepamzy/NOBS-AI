from fastapi import APIRouter

from app.schemas.voice import VoicePresetRead
from services.voice.catalog import VOICE_PRESETS

router = APIRouter(prefix="/voices", tags=["voices"])


@router.get("", response_model=list[VoicePresetRead])
def list_voices() -> list[VoicePresetRead]:
    return [VoicePresetRead(id=p.id, name=p.name, description=p.description) for p in VOICE_PRESETS]
