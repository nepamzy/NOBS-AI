from pydantic import BaseModel


class VoicePresetRead(BaseModel):
    id: str
    name: str
    description: str
