def _create_project_and_video(client, db_session, stage="completed"):
    from app.models.enums import PipelineStage
    from app.models.video import Video

    project_response = client.post("/projects", json={"name": "Weekly Stories"})
    project_id = project_response.json()["id"]

    video = Video(
        project_id=project_id,
        topic="Test video",
        target_duration_seconds=300,
        stage=PipelineStage[stage.upper()],
        storyboard_approved=True,
        final_video_path="/tmp/fake-final.mp4",
    )
    db_session.add(video)
    db_session.flush()
    return video


def test_upload_returns_402_when_youtube_not_configured(client, db_session):
    video = _create_project_and_video(client, db_session)

    response = client.post(
        f"/videos/{video.id}/youtube/upload",
        json={"title": "Title", "description": "Description"},
    )
    assert response.status_code == 402
    assert "GOOGLE_YOUTUBE" in response.json()["detail"]


def test_upload_requires_a_finished_video_file(client, db_session):
    video = _create_project_and_video(client, db_session)
    video.final_video_path = None
    db_session.flush()

    response = client.post(
        f"/videos/{video.id}/youtube/upload",
        json={"title": "Title", "description": "Description"},
    )
    assert response.status_code == 409


def test_publish_requires_an_upload_first(client, db_session):
    video = _create_project_and_video(client, db_session)

    response = client.post(f"/videos/{video.id}/youtube/publish")
    assert response.status_code == 409


def test_publish_returns_402_when_youtube_not_configured(client, db_session):
    video = _create_project_and_video(client, db_session)
    video.youtube_video_id = "yt_fake_id"
    db_session.flush()

    response = client.post(f"/videos/{video.id}/youtube/publish")
    assert response.status_code == 402


def test_add_and_list_video_feedback(client, db_session):
    video = _create_project_and_video(client, db_session)

    response = client.post(f"/videos/{video.id}/feedback", json={"note": "Great hook!"})
    assert response.status_code == 201
    assert response.json()["note"] == "Great hook!"

    list_response = client.get(f"/projects/{video.project_id}/feedback")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["note"] == "Great hook!"
