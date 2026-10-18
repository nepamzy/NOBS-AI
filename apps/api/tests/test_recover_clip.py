import uuid

from app.models.enums import JobStatus, PipelineStage
from app.models.script import Scene, Script
from app.models.video import Video
from app.models.video_clip import VideoClip
from tests.test_continue import _queue
from tests.test_restart import _make_video


def _video_with_scenes(client, db_session, stage, scene_count=2, detail=""):
    video = _make_video(client)
    row = db_session.get(Video, uuid.UUID(video["id"]))
    row.stage = stage
    row.stage_detail = detail
    row.storyboard_approved = True
    script = Script(
        video_id=row.id,
        title="t",
        hook="h",
        estimated_duration_seconds=10,
        word_count=5,
    )
    script.scenes = [
        Scene(order=i + 1, narration=f"n{i + 1}", visual_prompt="v", duration_seconds=5)
        for i in range(scene_count)
    ]
    db_session.add(script)
    db_session.commit()
    return video["id"], [scene.id for scene in script.scenes]


def test_recover_attaches_the_job_to_the_first_unfinished_scene(client, db_session, monkeypatch):
    queued = _queue(monkeypatch)
    video_id, scene_ids = _video_with_scenes(
        client,
        db_session,
        PipelineStage.FAILED,
        detail="Crashed at 'video_generation': RuntimeError: lost",
    )
    db_session.add(
        VideoClip(
            video_id=uuid.UUID(video_id),
            scene_id=scene_ids[0],
            provider="WanEngine",
            status=JobStatus.SUCCEEDED,
            clip_path="scene1.mp4",
        )
    )
    db_session.commit()
    queued.clear()

    response = client.post(
        f"/videos/{video_id}/recover-clip", json={"runpod_job_id": "abc-123_XYZ"}
    )

    assert response.status_code == 200
    assert response.json()["stage"] == "video_generation"
    assert queued == [(video_id, False)]
    recovered = (
        db_session.query(VideoClip)
        .filter(VideoClip.provider_job_id == "abc-123_XYZ")
        .one()
    )
    assert recovered.scene_id == scene_ids[1]
    assert recovered.status == JobStatus.QUEUED


def test_recover_works_on_a_stuck_video_in_video_generation(client, db_session, monkeypatch):
    queued = _queue(monkeypatch)
    video_id, scene_ids = _video_with_scenes(client, db_session, PipelineStage.VIDEO_GENERATION)
    queued.clear()

    response = client.post(f"/videos/{video_id}/recover-clip", json={"runpod_job_id": "job9876"})

    assert response.status_code == 200
    assert queued == [(video_id, False)]
    recovered = db_session.query(VideoClip).filter(VideoClip.provider_job_id == "job9876").one()
    assert recovered.scene_id == scene_ids[0]


def test_recover_refuses_a_video_that_failed_elsewhere(client, db_session, monkeypatch):
    queued = _queue(monkeypatch)
    video_id, _ = _video_with_scenes(
        client,
        db_session,
        PipelineStage.FAILED,
        detail="Crashed at 'voice': RuntimeError: tts down",
    )
    queued.clear()

    response = client.post(f"/videos/{video_id}/recover-clip", json={"runpod_job_id": "job1234"})

    assert response.status_code == 409
    assert queued == []


def test_recover_refuses_a_job_id_already_attached(client, db_session, monkeypatch):
    queued = _queue(monkeypatch)
    video_id, scene_ids = _video_with_scenes(client, db_session, PipelineStage.VIDEO_GENERATION)
    db_session.add(
        VideoClip(
            video_id=uuid.UUID(video_id),
            scene_id=scene_ids[0],
            provider="recovered-runpod",
            status=JobStatus.QUEUED,
            provider_job_id="job5555",
        )
    )
    db_session.commit()
    queued.clear()

    response = client.post(f"/videos/{video_id}/recover-clip", json={"runpod_job_id": "job5555"})

    assert response.status_code == 409
    assert queued == []


def test_recover_refuses_when_every_scene_already_has_a_clip(client, db_session, monkeypatch):
    queued = _queue(monkeypatch)
    video_id, scene_ids = _video_with_scenes(
        client, db_session, PipelineStage.VIDEO_GENERATION, scene_count=1
    )
    db_session.add(
        VideoClip(
            video_id=uuid.UUID(video_id),
            scene_id=scene_ids[0],
            provider="WanEngine",
            status=JobStatus.SUCCEEDED,
            clip_path="scene1.mp4",
        )
    )
    db_session.commit()
    queued.clear()

    response = client.post(f"/videos/{video_id}/recover-clip", json={"runpod_job_id": "job7777"})

    assert response.status_code == 409
    assert queued == []


def test_recover_rejects_a_malformed_job_id(client, db_session, monkeypatch):
    _queue(monkeypatch)
    video_id, _ = _video_with_scenes(client, db_session, PipelineStage.VIDEO_GENERATION)

    response = client.post(
        f"/videos/{video_id}/recover-clip", json={"runpod_job_id": "bad id; drop"}
    )

    assert response.status_code == 422


def test_recover_unknown_video_is_404(client):
    response = client.post(
        f"/videos/{uuid.uuid4()}/recover-clip", json={"runpod_job_id": "job8888"}
    )
    assert response.status_code == 404
