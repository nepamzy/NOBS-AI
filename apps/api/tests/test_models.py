from app.models.enums import PipelineStage
from app.models.project import Project
from app.models.script import Scene, Script
from app.models.user import User
from app.models.video import Video


def test_video_pipeline_defaults_and_relationships(db_session):
    user = User(email="nobert@local", display_name="Nobert", password_hash="test-hash")
    db_session.add(user)
    db_session.flush()

    project = Project(owner_id=user.id, name="Test Project")
    db_session.add(project)
    db_session.flush()

    video = Video(
        project_id=project.id,
        topic="5 mistakes new developers make",
        target_duration_seconds=180,
    )
    db_session.add(video)
    db_session.flush()

    assert video.stage == PipelineStage.TOPIC
    assert video.storyboard_approved is False
    assert video.project.id == project.id
    assert project.videos == [video]


def test_script_scenes_ordered_and_cascade_delete(db_session):
    user = User(email="nobert@local", display_name="Nobert", password_hash="test-hash")
    db_session.add(user)
    db_session.flush()
    project = Project(owner_id=user.id, name="Test Project")
    db_session.add(project)
    db_session.flush()
    video = Video(project_id=project.id, topic="topic", target_duration_seconds=60)
    db_session.add(video)
    db_session.flush()

    script = Script(
        video_id=video.id,
        title="Title",
        hook="Hook",
        estimated_duration_seconds=60,
        word_count=100,
    )
    script.scenes = [
        Scene(order=2, narration="second", visual_prompt="b", duration_seconds=8),
        Scene(order=1, narration="first", visual_prompt="a", duration_seconds=6),
    ]
    db_session.add(script)
    db_session.flush()
    db_session.refresh(script)

    assert [s.narration for s in script.scenes] == ["first", "second"]

    db_session.delete(video)
    db_session.flush()

    assert db_session.get(Script, script.id) is None
    assert db_session.query(Scene).filter(Scene.script_id == script.id).count() == 0
