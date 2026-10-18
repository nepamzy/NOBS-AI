import uuid

from app.models.enums import PipelineStage
from app.models.video import Video
from tests.test_restart import _make_video


def _failed_video(client, db_session, detail):
    video = _make_video(client)
    row = db_session.get(Video, uuid.UUID(video["id"]))
    row.stage = PipelineStage.FAILED
    row.stage_detail = detail
    row.storyboard_approved = True
    db_session.commit()
    return video["id"]


def _queue(monkeypatch):
    import app.routers.videos as videos_router

    queued = []
    monkeypatch.setattr(
        videos_router,
        "enqueue_pipeline_start",
        lambda video_id, run_research: queued.append((str(video_id), run_research)),
    )
    return queued


def test_continue_resumes_at_the_stage_that_crashed_and_keeps_approval(
    client, db_session, monkeypatch
):
    queued = _queue(monkeypatch)
    video_id = _failed_video(
        client, db_session, "Crashed at 'video_generation': JobTimeoutException: 180 seconds"
    )
    queued.clear()

    response = client.post(f"/videos/{video_id}/continue")

    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "video_generation"
    assert body["stage_detail"] == ""
    assert body["storyboard_approved"] is True
    assert queued == [(video_id, False)]


def test_continue_rejects_a_video_that_is_not_failed(client, db_session, monkeypatch):
    _queue(monkeypatch)
    video = _make_video(client)

    response = client.post(f"/videos/{video['id']}/continue")

    assert response.status_code == 409


def test_continue_refuses_when_the_failed_stage_is_unknown(client, db_session, monkeypatch):
    _queue(monkeypatch)
    video_id = _failed_video(client, db_session, "something odd happened")

    response = client.post(f"/videos/{video_id}/continue")

    assert response.status_code == 409
    assert "Restart" in response.json()["detail"]


def test_continue_unknown_video_is_404(client):
    response = client.post(f"/videos/{uuid.uuid4()}/continue")
    assert response.status_code == 404
