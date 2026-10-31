def _create_project(db_session):
    from app.auth.security import hash_password
    from app.models.enums import UserRole
    from app.models.project import Project
    from app.models.user import User

    owner = User(
        email="auto-retry-owner@local",
        display_name="Owner",
        password_hash=hash_password("x"),
        role=UserRole.ADMIN,
    )
    db_session.add(owner)
    db_session.flush()
    project = Project(owner_id=owner.id, name="Auto Retry Test")
    db_session.add(project)
    db_session.flush()
    return project


def _make_failed_video(db_session, project, stage_detail, auto_retry_count=0):
    from app.models.enums import PipelineStage
    from app.models.video import Video

    video = Video(
        project_id=project.id,
        topic="t",
        target_duration_seconds=60,
        stage=PipelineStage.FAILED,
        stage_detail=stage_detail,
        auto_retry_count=auto_retry_count,
    )
    db_session.add(video)
    db_session.flush()
    return video


def _patch_enqueue(monkeypatch):
    """check_and_retry_crashed_videos imports enqueue_pipeline_start locally
    (same reasoning as pipeline.py — avoids an apps/api <-> services import
    cycle), so it always looks it up fresh from app.jobs.queue at call time;
    patch it there, not on the auto_retry module."""
    import app.jobs.queue as queue_module

    enqueued: list = []
    monkeypatch.setattr(
        queue_module,
        "enqueue_pipeline_start",
        lambda video_id, run_research: enqueued.append(video_id),
    )
    return enqueued


def test_crashed_video_generation_gets_auto_retried(db_session, monkeypatch):
    from app.models.enums import PipelineStage

    import services.scheduling.auto_retry as auto_retry_module

    enqueued = _patch_enqueue(monkeypatch)

    project = _create_project(db_session)
    video = _make_failed_video(
        db_session,
        project,
        "Crashed at 'video_generation': RuntimeError: Scene 1 clip: Runpod no longer has job x",
    )

    results = auto_retry_module.check_and_retry_crashed_videos(db_session)

    assert len(results) == 1
    assert "auto-retried" in results[0]
    db_session.refresh(video)
    assert video.stage == PipelineStage.VIDEO_GENERATION
    assert video.auto_retry_count == 1
    assert "1/2" in video.stage_detail
    assert enqueued == [video.id]


def test_auto_retry_stops_once_the_cap_is_reached(db_session, monkeypatch):
    from app.models.enums import PipelineStage

    import services.scheduling.auto_retry as auto_retry_module

    enqueued = _patch_enqueue(monkeypatch)

    project = _create_project(db_session)
    video = _make_failed_video(
        db_session,
        project,
        "Crashed at 'video_generation': RuntimeError: still broken",
        auto_retry_count=2,  # already at _MAX_AUTO_RETRIES
    )

    results = auto_retry_module.check_and_retry_crashed_videos(db_session)

    assert results == []
    assert enqueued == []
    db_session.refresh(video)
    assert video.stage == PipelineStage.FAILED  # left for a human, not retried forever
    assert video.auto_retry_count == 2


def test_crash_at_a_non_resumable_stage_is_not_retried(db_session, monkeypatch):
    from app.models.enums import PipelineStage

    import services.scheduling.auto_retry as auto_retry_module

    enqueued = _patch_enqueue(monkeypatch)

    project = _create_project(db_session)
    video = _make_failed_video(db_session, project, "Crashed at 'topic': ValueError: x")

    results = auto_retry_module.check_and_retry_crashed_videos(db_session)

    assert results == []
    assert enqueued == []
    db_session.refresh(video)
    assert video.stage == PipelineStage.FAILED
    assert video.auto_retry_count == 0


def test_a_failed_video_with_no_parseable_crash_reason_is_skipped(db_session, monkeypatch):
    import services.scheduling.auto_retry as auto_retry_module

    enqueued = _patch_enqueue(monkeypatch)

    project = _create_project(db_session)
    _make_failed_video(db_session, project, "")

    results = auto_retry_module.check_and_retry_crashed_videos(db_session)

    assert results == []
    assert enqueued == []


def test_non_failed_videos_are_left_alone(db_session, monkeypatch):
    from app.models.enums import PipelineStage
    from app.models.video import Video

    import services.scheduling.auto_retry as auto_retry_module

    enqueued = _patch_enqueue(monkeypatch)

    project = _create_project(db_session)
    db_session.add(
        Video(
            project_id=project.id,
            topic="t",
            target_duration_seconds=60,
            stage=PipelineStage.COMPLETED,
        )
    )
    db_session.flush()

    results = auto_retry_module.check_and_retry_crashed_videos(db_session)

    assert results == []
    assert enqueued == []
