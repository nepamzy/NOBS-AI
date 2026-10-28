"""Covers app/jobs/clip_tasks.py's own crash-recording wrapper around the
clip pipeline — advance_clip_stage itself is covered at a lower level in
test_clip_pipeline.py, this is specifically about what happens when it
raises something unexpected (ffmpeg crash, network blip, bug) rather than
the well-behaved ClipPipelineBlocked."""

from sqlalchemy.orm import sessionmaker


def test_advance_clip_pipeline_records_failure_on_unexpected_crash(
    db_session, monkeypatch, tmp_path
):
    import app.jobs.clip_tasks as clip_tasks_module
    from app.models.enums import ClipJobStage
    from app.models.source_video import SourceVideo
    from app.models.user import User

    from services.clipping.pipeline import ClipPipelineContext
    from services.storage.backend import LocalStorageBackend

    user = User(email="nobert@local", display_name="Nobert", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    source_video = SourceVideo(
        owner_id=user.id,
        original_filename="source.mp4",
        source_path=str(tmp_path / "source.mp4"),
    )
    db_session.add(source_video)
    db_session.commit()
    source_video_id = str(source_video.id)

    # _record_clip_failure (like the main pipeline's _record_failure) opens
    # a brand-new session via SessionLocal(). Bind it to this test's own
    # connection — not a separate pool connection — so its write is visible
    # to db_session below and still rolled back at the end of the test,
    # the same trick the db_session fixture itself uses.
    monkeypatch.setattr(
        clip_tasks_module, "SessionLocal", sessionmaker(bind=db_session.get_bind())
    )

    def fake_advance_clip_stage(source_video, db, ctx):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(clip_tasks_module, "advance_clip_stage", fake_advance_clip_stage)
    monkeypatch.setattr(
        clip_tasks_module,
        "_build_clip_context",
        lambda: ClipPipelineContext(
            transcription_engine=None,
            llm_provider="",
            llm_api_key="",
            llm_model="",
            storage_root=str(tmp_path),
            storage_backend=LocalStorageBackend(),
        ),
    )

    result = clip_tasks_module.advance_clip_pipeline(source_video_id)

    assert result == "failed at uploaded: ffmpeg exploded"
    db_session.expire_all()
    refreshed = db_session.get(SourceVideo, source_video.id)
    assert refreshed.stage == ClipJobStage.FAILED
    assert refreshed.stage_detail == "Crashed at 'uploaded': RuntimeError: ffmpeg exploded"
