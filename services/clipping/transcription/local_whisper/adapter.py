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

import logging
from pathlib import Path

from services.clipping.transcription.engine import TranscriptionEngine, TranscriptResult, Word
from services.common.errors import EngineNotConfiguredError

logger = logging.getLogger(__name__)

_GIB = 1024**3
_SIZES = ["tiny", "base", "small", "medium"]  # anything else counts as heavier than all of these


def _memory_limit_bytes() -> int | None:
    """The container's memory ceiling (cgroup v2, then v1), or None when
    unlimited/unreadable (e.g. a dev machine)."""
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            raw = Path(path).read_text().strip()
        except OSError:
            continue
        if raw.isdigit() and int(raw) < 1 << 60:  # v1 reports a huge number for "no limit"
            return int(raw)
    return None


def effective_model_size(requested: str, limit_bytes: int | None = None) -> str:
    """Never pick a Whisper model the machine can't hold. On Render's 512 MB
    worker, "small" gets the whole process killed (OOM) with no error and no
    trace — that stranded every Smart Clipping upload at "Queued", exactly as
    it earlier stranded Chatterbox voiceovers. So: <= ~1 GB of memory caps the
    model at "tiny", <= ~2 GB at "base"; anything bigger (or unknown) honours
    the request."""
    limit = _memory_limit_bytes() if limit_bytes is None else limit_bytes
    if limit is None:
        return requested
    if limit <= 1.1 * _GIB:
        ceiling = "tiny"
    elif limit <= 2.2 * _GIB:
        ceiling = "base"
    else:
        return requested
    rank = _SIZES.index(requested) if requested in _SIZES else len(_SIZES)
    if rank > _SIZES.index(ceiling):
        logger.warning(
            "Whisper model %r doesn't fit in %d MB of memory; using %r instead",
            requested, limit // (1024 * 1024), ceiling,
        )
        return ceiling
    return requested


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

            size = effective_model_size(self._model_size)
            self._model = WhisperModel(size, device="auto", compute_type="int8")
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
