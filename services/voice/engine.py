"""Voice engine abstraction (CLAUDE.md Part 3):

    VOICE_ENGINE -> Chatterbox | ElevenLabs | OpenAI TTS | future

Callers depend only on this interface, never on a specific provider, so
swapping Chatterbox for something else later doesn't touch the pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VoiceoverResult:
    audio_path: str
    duration_seconds: float
    word_timestamps: list[dict] = field(default_factory=list)  # [{"word","start","end"}]


class VoiceEngine(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice_preset: str, output_path: str) -> VoiceoverResult: ...
