"""Transcription engine abstraction (mirrors services/voice/engine.py) —
so a cloud STT provider can be added later without touching the pipeline.
Only one real implementation for now: services/clipping/transcription/
local_whisper (see that module's docstring for why)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Word:
    word: str
    start: float
    end: float


@dataclass
class TranscriptResult:
    full_text: str
    words: list[Word] = field(default_factory=list)


class TranscriptionEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> TranscriptResult: ...
