from datetime import datetime, timezone


class _FixedDatetime(datetime):
    """Lets the test pin "now" without needing real wall-clock timing."""

    _fixed = datetime(2026, 10, 5, 16, 0, tzinfo=timezone.utc)  # a Monday

    @classmethod
    def now(cls, tz=None):
        return cls._fixed


def _create_project_and_user(db_session):
    from app.auth.security import hash_password
    from app.models.enums import UserRole
    from app.models.project import Project
    from app.models.user import User

    owner = User(
        email="scheduler-owner@local",
        display_name="Owner",
        password_hash=hash_password("x"),
        role=UserRole.ADMIN,
    )
    db_session.add(owner)
    db_session.flush()
    project = Project(owner_id=owner.id, name="Weekly Stories")
    db_session.add(project)
    db_session.flush()
    return project


def test_due_schedule_creates_a_video(db_session, monkeypatch):
    import app.routers.videos as videos_router
    from app.models.upload_schedule import UploadSchedule

    enqueued = []

    def fake_enqueue(video_id, run_research):
        enqueued.append(video_id)

    monkeypatch.setattr(videos_router, "enqueue_pipeline_start", fake_enqueue)

    project = _create_project_and_user(db_session)
    schedule = UploadSchedule(
        project_id=project.id,
        day_of_week=0,  # Monday — matches _FixedDatetime
        trigger_time="16:00",
        topic="Storytelling: Hero's Journey",
        target_duration_seconds=300,
    )
    db_session.add(schedule)
    db_session.flush()

    import services.scheduling.scheduler as scheduler_module

    monkeypatch.setattr(scheduler_module, "datetime", _FixedDatetime)

    results = scheduler_module.check_and_trigger_due_schedules(db_session)

    assert len(results) == 1
    assert "created video" in results[0]
    assert len(enqueued) == 1
    db_session.refresh(schedule)
    assert schedule.last_triggered_on == "2026-10-05"


def test_does_not_fire_twice_same_day(db_session, monkeypatch):
    import app.routers.videos as videos_router
    from app.models.upload_schedule import UploadSchedule

    monkeypatch.setattr(videos_router, "enqueue_pipeline_start", lambda *a, **k: "job")

    project = _create_project_and_user(db_session)
    schedule = UploadSchedule(
        project_id=project.id,
        day_of_week=0,
        trigger_time="16:00",
        topic="x",
        target_duration_seconds=300,
        last_triggered_on="2026-10-05",  # already fired today
    )
    db_session.add(schedule)
    db_session.flush()

    import services.scheduling.scheduler as scheduler_module

    monkeypatch.setattr(scheduler_module, "datetime", _FixedDatetime)

    results = scheduler_module.check_and_trigger_due_schedules(db_session)
    assert results == []


def test_wrong_day_or_time_does_not_fire(db_session, monkeypatch):
    import app.routers.videos as videos_router
    from app.models.upload_schedule import UploadSchedule

    monkeypatch.setattr(videos_router, "enqueue_pipeline_start", lambda *a, **k: "job")

    project = _create_project_and_user(db_session)
    db_session.add(
        UploadSchedule(
            project_id=project.id,
            day_of_week=1,  # Tuesday, not Monday
            trigger_time="16:00",
            topic="x",
            target_duration_seconds=300,
        )
    )
    db_session.add(
        UploadSchedule(
            project_id=project.id,
            day_of_week=0,
            trigger_time="09:00",  # wrong time
            topic="x",
            target_duration_seconds=300,
        )
    )
    db_session.flush()

    import services.scheduling.scheduler as scheduler_module

    monkeypatch.setattr(scheduler_module, "datetime", _FixedDatetime)

    results = scheduler_module.check_and_trigger_due_schedules(db_session)
    assert results == []


def test_disabled_schedule_does_not_fire(db_session, monkeypatch):
    import app.routers.videos as videos_router
    from app.models.upload_schedule import UploadSchedule

    monkeypatch.setattr(videos_router, "enqueue_pipeline_start", lambda *a, **k: "job")

    project = _create_project_and_user(db_session)
    db_session.add(
        UploadSchedule(
            project_id=project.id,
            day_of_week=0,
            trigger_time="16:00",
            topic="x",
            target_duration_seconds=300,
            enabled=False,
        )
    )
    db_session.flush()

    import services.scheduling.scheduler as scheduler_module

    monkeypatch.setattr(scheduler_module, "datetime", _FixedDatetime)

    results = scheduler_module.check_and_trigger_due_schedules(db_session)
    assert results == []
