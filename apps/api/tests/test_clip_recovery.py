"""Smart Clipping uploads that used to sit at "Queued" forever: a transcription
model too big for the worker (OOM kill = no trace), a video with no audio, and
a job killed mid-run. Covers the memory guard, the clear no-audio message, the
attempt cap, restart recovery, the Retry endpoint and the playable source URL."""

import subprocess
from datetime import UTC, datetime, timedelta

import pytest
from app.jobs import clip_recovery, clip_tasks
from app.models.enums import ClipJobStage
from app.models.source_video import SourceVideo
from sqlalchemy.orm import sessionmaker

from services.clipping.audio import NO_AUDIO_MESSAGE, has_audio_stream
from services.clipping.pipeline import ClipPipelineBlocked, ClipPipelineContext, advance_clip_stage
from services.clipping.transcription.local_whisper.adapter import effective_model_size
from services.storage.backend import LocalStorageBackend

MB = 1024 * 1024


# ---- memory guard ---------------------------------------------------------


@pytest.mark.parametrize(
    ("limit_mb", "requested", "expected"),
    [
        (512, "small", "tiny"),  # the real Render worker that got OOM-killed
        (512, "medium", "tiny"),
        (512, "large-v3", "tiny"),
        (512, "tiny", "tiny"),
        (1024, "base", "tiny"),
        (2048, "small", "base"),
        (2048, "tiny", "tiny"),
        (4096, "small", "small"),
        (8192, "medium", "medium"),
    ],
)
def test_model_is_capped_to_what_the_machine_can_hold(limit_mb, requested, expected):
    assert effective_model_size(requested, limit_mb * MB) == expected


def test_unreadable_memory_limit_honours_the_request(monkeypatch):
    from services.clipping.transcription.local_whisper import adapter

    monkeypatch.setattr(adapter, "_memory_limit_bytes", lambda: None)
    assert effective_model_size("small") == "small"  # e.g. a dev machine


# ---- no audio ---------------------------------------------------------------


@pytest.fixture(scope="module")
def silent_and_sound(tmp_path_factory):
    d = tmp_path_factory.mktemp("av")
    silent, sound = d / "silent.mp4", d / "sound.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
                    "-pix_fmt", "yuv420p", str(silent)], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-pix_fmt", "yuv420p",
                    "-shortest", str(sound)], check=True, capture_output=True)
    return silent, sound


def test_audio_detection(silent_and_sound, tmp_path):
    silent, sound = silent_and_sound
    assert has_audio_stream(str(sound)) is True
    assert has_audio_stream(str(silent)) is False
    # a file that can't be inspected -> assume audio and let ffmpeg report the real problem
    assert has_audio_stream(str(tmp_path / "does-not-exist.mp4")) is True


def test_silent_video_is_blocked_with_a_clear_message_not_a_crash(
    db_session, client, silent_and_sound, tmp_path
):
    silent, _ = silent_and_sound

    class MustNotRun:
        def transcribe(self, path):
            raise AssertionError("transcription should not start for a silent video")

    sv = SourceVideo(owner_id=client.admin_user.id, original_filename="s.mp4",
                     source_path=str(silent))
    db_session.add(sv)
    db_session.flush()
    ctx = ClipPipelineContext(transcription_engine=MustNotRun(), llm_provider="", llm_api_key="",
                              llm_model="", storage_root=str(tmp_path),
                              storage_backend=LocalStorageBackend())

    with pytest.raises(ClipPipelineBlocked):
        advance_clip_stage(sv, db_session, ctx)
    assert sv.stage == ClipJobStage.UPLOADED and sv.stage_detail == NO_AUDIO_MESSAGE
    assert "no audio track" in sv.stage_detail


# ---- attempts cap ----------------------------------------------------------------


def _bind_session(monkeypatch, db_session):
    monkeypatch.setattr(clip_tasks, "SessionLocal", sessionmaker(bind=db_session.get_bind()))


def _stub_context(monkeypatch, tmp_path):
    monkeypatch.setattr(
        clip_tasks, "_build_clip_context",
        lambda: ClipPipelineContext(transcription_engine=None, llm_provider="", llm_api_key="",
                                    llm_model="", storage_root=str(tmp_path),
                                    storage_backend=LocalStorageBackend()),
    )


def test_each_job_start_is_counted_and_a_third_failure_stops_the_loop(
    db_session, client, monkeypatch, tmp_path
):
    _bind_session(monkeypatch, db_session)
    _stub_context(monkeypatch, tmp_path)
    ran = []

    def fake_advance(sv, db, ctx):
        ran.append(sv.attempts)
        raise ClipPipelineBlocked("transcribing", "pretend this was killed")  # ends the job

    monkeypatch.setattr(clip_tasks, "advance_clip_stage", fake_advance)
    sv = SourceVideo(owner_id=client.admin_user.id, original_filename="a.mp4", source_path="p")
    db_session.add(sv)
    db_session.commit()
    sv_id = str(sv.id)

    for expected_attempts in (1, 2, 3):
        sv.stage_detail = ""  # as after a restart: no recorded reason
        db_session.commit()
        clip_tasks.advance_clip_pipeline(sv_id)
        db_session.refresh(sv)
        assert sv.attempts == expected_attempts

    sv.stage_detail = ""
    db_session.commit()
    result = clip_tasks.advance_clip_pipeline(sv_id)
    db_session.refresh(sv)
    assert result.startswith("gave up")
    assert sv.stage_detail == clip_tasks.GIVE_UP_MESSAGE and "Retry" in sv.stage_detail
    assert ran == [1, 2, 3]  # the 4th attempt never ran any work


# ---- restart recovery ----------------------------------------------------------------


def test_worker_start_requeues_only_genuinely_interrupted_uploads(
    db_session, client, monkeypatch
):
    queued = []
    monkeypatch.setattr(clip_recovery, "enqueue_clip_pipeline_start", lambda i: queued.append(i))
    old = datetime.now(UTC) - timedelta(minutes=10)

    def make(name, **fields):
        sv = SourceVideo(owner_id=client.admin_user.id, original_filename=name, source_path="p",
                         **fields)
        db_session.add(sv)
        db_session.flush()
        return sv

    interrupted = make("interrupted", updated_at=old)
    fresh = make("fresh")  # touched just now: may still be waiting in the queue
    blocked = make("blocked", updated_at=old, stage_detail="needs an LLM key")
    exhausted = make("exhausted", updated_at=old, attempts=3)
    done = make("done", updated_at=old, stage=ClipJobStage.COMPLETED)

    results = clip_recovery.requeue_interrupted_source_videos(db_session)

    assert queued == [interrupted.id]
    assert len(results) == 2
    # an immediate second restart finds nothing: the re-queued one was just touched and
    # the exhausted one now carries its reason
    assert clip_recovery.requeue_interrupted_source_videos(db_session) == []
    assert queued == [interrupted.id]
    assert exhausted.stage_detail == clip_tasks.GIVE_UP_MESSAGE
    assert blocked.stage_detail == "needs an LLM key"
    assert fresh.stage_detail == "" and done.stage_detail == ""


# ---- Retry endpoint + playable URL ---------------------------------------------------


def _source(db_session, client, **fields) -> SourceVideo:
    sv = SourceVideo(owner_id=client.admin_user.id, original_filename="v.mp4",
                     source_path=fields.pop("source_path", "p"), **fields)
    db_session.add(sv)
    db_session.flush()
    return sv


def test_retry_resets_and_requeues(client, db_session):
    sv = _source(db_session, client, attempts=3, stage_detail="Stopped after 3 attempts")
    response = client.post(f"/source-videos/{sv.id}/retry")
    assert response.status_code == 200, response.text
    db_session.refresh(sv)
    assert sv.attempts == 0 and sv.stage_detail == "" and sv.stage == ClipJobStage.UPLOADED
    assert client.enqueued_clip_jobs[-1]["source_video_id"] == sv.id


def test_retry_marks_even_an_already_clean_upload_as_just_touched(client, db_session):
    old = datetime.now(UTC) - timedelta(minutes=30)
    sv = _source(db_session, client, updated_at=old)  # nothing else to reset
    client.post(f"/source-videos/{sv.id}/retry")
    db_session.refresh(sv)
    assert datetime.now(UTC) - sv.updated_at < timedelta(minutes=1)


def test_retry_of_a_failed_upload_resumes_after_the_transcript(client, db_session):
    with_transcript = _source(db_session, client, stage=ClipJobStage.FAILED,
                              transcript_path="t.json", stage_detail="Crashed at 'x'")
    without = _source(db_session, client, stage=ClipJobStage.FAILED)
    client.post(f"/source-videos/{with_transcript.id}/retry")
    client.post(f"/source-videos/{without.id}/retry")
    db_session.refresh(with_transcript)
    db_session.refresh(without)
    assert with_transcript.stage == ClipJobStage.SELECTING_CLIPS  # transcript kept, not redone
    assert without.stage == ClipJobStage.UPLOADED


def test_retry_refuses_finished_and_other_peoples_uploads(client, db_session):
    from app.auth.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    done = _source(db_session, client, stage=ClipJobStage.COMPLETED)
    assert client.post(f"/source-videos/{done.id}/retry").status_code == 409

    other = User(email="o@local", display_name="O", password_hash=hash_password("pw-12345678"),
                 role=UserRole.USER)
    db_session.add(other)
    db_session.flush()
    theirs = SourceVideo(owner_id=other.id, original_filename="x", source_path="p")
    db_session.add(theirs)
    db_session.flush()
    assert client.post(f"/source-videos/{theirs.id}/retry").status_code == 404


def test_uploads_expose_a_playable_url_and_claude_sources_have_none(client, db_session):
    url = "https://x.supabase.co/storage/v1/object/public/nobs-ai/clips/abc/source.mp4"
    _source(db_session, client, source_path=url)
    _source(db_session, client, source_path="external:claude")

    rows = {r["source_url"] is None: r for r in client.get("/source-videos").json()}
    assert rows[False]["source_url"] == url
    assert rows[True]["source_url"] is None
    assert "source_path" not in rows[False]  # the raw path isn't exposed
