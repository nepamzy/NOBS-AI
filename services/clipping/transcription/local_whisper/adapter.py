"""Local Whisper transcription via faster-whisper (CTranslate2, MIT
license) — runs on CPU, no GPU needed, so unlike LocalWanEngine this does
NOT require Nobert's laptop to be on; it runs on the existing Render
worker. No API key, no per-call cost — like services/rendering/ffmpeg's
own docstring says about ffmpeg itself, this is real local compute, not a
stub behind ApprovalRequiredError.

First call downloads the chosen model from Hugging Face (a few hundred MB
for "small") and caches it on disk — one-time cost in time/bandwidth, not
money. A long source video can take several minutes to transcribe on CPU;
this runs inside the worker job, not a request handler, so it doesn't
block the API.
"""

from pathlib import Path

from services.clipping.transcription.engine import TranscriptionEngine, TranscriptResult, Word
from services.common.errors import EngineNotConfiguredError


class LocalWhisperEngine(TranscriptionEngine):
    def __init__(self, model_size: str = "small"):
        self._model_size = model_size
        self._model = None  # loaded lazily so importing this module stays cheap

    def _require_available(self) -> None:
        try:
            import faster_whisper  # noqa: F401
        except ImportError as exc:
            raise EngineNotConfiguredError(
                "faster-whisper isn't installed — add it to requirements.txt "
                "(it is, as of this feature; redeploy if this still fires)."
            ) from exc

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_size, device="auto", compute_type="int8")
        return self._model

    def transcribe(self, audio_path: str) -> TranscriptResult:
        self._require_available()
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._load_model()
        segments, _info = model.transcribe(audio_path, word_timestamps=True, vad_filter=True)

        words: list[Word] = []
        full_text_parts: list[str] = []
        for segment in segments:
            full_text_parts.append(segment.text.strip())
            for word in segment.words or []:
                words.append(Word(word=word.word.strip(), start=word.start, end=word.end))

        return TranscriptResult(full_text=" ".join(full_text_parts), words=words)
