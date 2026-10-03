import pytest
from app.models.clip import Clip
from app.models.enums import ClipJobStage
from app.models.source_video import SourceVideo
from app.models.user import User

from services.clipping.pipeline import ClipPipelineBlocked, ClipPipelineContext, advance_clip_stage
from services.clipping.selector import ClipSelection
from services.clipping.transcription.engine import TranscriptionEngine, TranscriptResult, Word
from services.common.errors import EngineNotConfiguredError
from services.storage.backend import LocalStorageBackend


def _make_source_video(db_session, tmp_path) -> SourceVideo:
    user = User(email="nobert@local", display_name="Nobert", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"fake video bytes")
    video = SourceVideo(
        owner_id=user.id, original_filename="source.mp4", source_path=str(source_path)
    )
    db_session.add(video)
    db_session.flush()
    return video


class _FakeTranscriptionEngine(TranscriptionEngine):
    def transcribe(self, audio_path):
        words = [
            Word(word="Hello", start=0.0, end=0.4),
            Word(word="world", start=0.5, end=0.9),
            Word(word="this", start=1.0, end=1.2),
            Word(word="is", start=1.3, end=1.4),
            Word(word="a", start=1.5, end=1.6),
            Word(word="test", start=1.7, end=2.0),
        ]
        return TranscriptResult(full_text="Hello world this is a test", words=words)


class _UnconfiguredTranscriptionEngine(TranscriptionEngine):
    def transcribe(self, audio_path):
        raise EngineNotConfiguredError("faster-whisper isn't installed")


def _ctx(tmp_path, transcription_engine=None, llm_provider="", llm_api_key=""):
    return ClipPipelineContext(
        transcription_engine=transcription_engine or _FakeTranscriptionEngine(),
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        llm_model="claude-sonnet-5",
        storage_root=str(tmp_path),
        storage_backend=LocalStorageBackend(),
    )


def test_uploaded_stage_transcribes_and_advances(db_session, monkeypatch, tmp_path):
    video = _make_source_video(db_session, tmp_path)
    monkeypatch.setattr(
        "services.clipping.audio.extract_audio_for_transcription", lambda *a, **k: None
    )

    advance_clip_stage(video, db_session, _ctx(tmp_path))

    assert video.stage == ClipJobStage.TRANSCRIBING
    assert video.transcript_path is not None


def test_uploaded_stage_blocks_when_transcription_not_available(db_session, monkeypatch, tmp_path):
    video = _make_source_video(db_session, tmp_path)
    monkeypatch.setattr(
        "services.clipping.audio.extract_audio_for_transcription", lambda *a, **k: None
    )

    ctx = _ctx(tmp_path, transcription_engine=_UnconfiguredTranscriptionEngine())
    with pytest.raises(ClipPipelineBlocked) as exc_info:
        advance_clip_stage(video, db_session, ctx)
    assert exc_info.value.stage == "transcribing"
    assert video.stage == ClipJobStage.UPLOADED  # never advanced past the gate


def test_selecting_clips_blocks_without_llm_config(db_session, monkeypatch, tmp_path):
    video = _make_source_video(db_session, tmp_path)
    monkeypatch.setattr(
        "services.clipping.audio.extract_audio_for_transcription", lambda *a, **k: None
    )
    monkeypatch.setattr("services.clipping.frames.extract_sample_frames", lambda *a, **k: [])
    ctx = _ctx(tmp_path)
    advance_clip_stage(video, db_session, ctx)  # -> TRANSCRIBING
    advance_clip_stage(video, db_session, ctx)  # -> SELECTING_CLIPS

    with pytest.raises(ClipPipelineBlocked) as exc_info:
        advance_clip_stage(video, db_session, ctx)
    assert exc_info.value.stage == "selecting_clips"
    assert "PAYMENT / COST WARNING" in video.stage_detail


def test_selecting_clips_creates_clip_rows(db_session, monkeypatch, tmp_path):
    video = _make_source_video(db_session, tmp_path)
    monkeypatch.setattr(
        "services.clipping.audio.extract_audio_for_transcription", lambda *a, **k: None
    )
    monkeypatch.setattr("services.clipping.frames.extract_sample_frames", lambda *a, **k: [])
    monkeypatch.setattr(
        "services.clipping.selector.select_clips",
        lambda *a, **k: [
            ClipSelection(title="Clip one", reason="Good hook", start_seconds=0.0, end_seconds=0.9)
        ],
    )

    ctx = _ctx(tmp_path, llm_provider="anthropic", llm_api_key="key123")
    advance_clip_stage(video, db_session, ctx)  # -> TRANSCRIBING
    advance_clip_stage(video, db_session, ctx)  # -> SELECTING_CLIPS
    advance_clip_stage(video, db_session, ctx)  # -> EXTRACTING

    assert video.stage == ClipJobStage.EXTRACTING
    clips = db_session.query(Clip).filter(Clip.source_video_id == video.id).all()
    assert len(clips) == 1
    assert clips[0].title == "Clip one"


def test_extracting_stage_cuts_and_captions_each_clip(db_session, monkeypatch, tmp_path):
    video = _make_source_video(db_session, tmp_path)
    video.stage = ClipJobStage.EXTRACTING
    video.transcript_path = str(tmp_path / "transcript.json")
    import json

    (tmp_path / "transcript.json").write_text(
        json.dumps(
            {
                "full_text": "Hello world",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.4},
                    {"word": "world", "start": 0.5, "end": 0.9},
                ],
            }
        )
    )
    db_session.add(
        Clip(source_video_id=video.id, start_seconds=0.0, end_seconds=0.9, title="Clip one")
    )
    db_session.flush()

    extract_calls = []
    caption_calls = []
    monkeypatch.setattr(
        "services.clipping.extractor.extract_clip",
        lambda *a, **k: extract_calls.append(a),
    )
    monkeypatch.setattr(
        "services.clipping.extractor.caption_clip",
        lambda raw, words, out, tmp: caption_calls.append(words) or open(out, "wb").close(),
    )

    advance_clip_stage(video, db_session, _ctx(tmp_path))

    assert video.stage == ClipJobStage.COMPLETED
    assert len(extract_calls) == 1
    assert len(caption_calls) == 1
    assert caption_calls[0][0]["word"] == "Hello"
    clip = db_session.query(Clip).filter(Clip.source_video_id == video.id).one()
    assert clip.clip_path is not None
