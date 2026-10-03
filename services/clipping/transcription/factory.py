from services.clipping.transcription.engine import TranscriptionEngine
from services.clipping.transcription.local_whisper.adapter import LocalWhisperEngine


def get_transcription_engine(provider: str, model_size: str) -> TranscriptionEngine:
    # Only one provider for now — structured as a factory anyway so a paid
    # cloud STT option can be added later (services/voice/factory.py and
    # services/video/factory.py follow the same shape) without touching
    # the pipeline that calls this.
    return LocalWhisperEngine(model_size)
