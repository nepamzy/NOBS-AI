def _make_video(client):
    project = client.post("/projects", json={"name": "Restart test"}).json()
    return client.post(
        "/videos",
        json={
            "project_id": project["id"],
            "topic": "a topic",
            "target_duration_seconds": 60,
            "run_research": False,
        },
    ).json()


def test_restart_resets_production_to_topic_and_requeues(client, monkeypatch):
    import app.routers.videos as videos_router

    requeued = []
    monkeypatch.setattr(
        videos_router,
        "enqueue_pipeline_start",
        lambda video_id, run_research: requeued.append((str(video_id), run_research)),
    )

    video = _make_video(client)
    requeued.clear()  # ignore the enqueue from creating the video
    response = client.post(f"/videos/{video['id']}/restart")

    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "topic"
    assert body["stage_progress_percent"] == 0
    assert body["storyboard_approved"] is False
    assert body["final_video_path"] is None
    assert requeued == [(video["id"], True)]


def test_restart_unknown_video_is_404(client):
    import uuid

    response = client.post(f"/videos/{uuid.uuid4()}/restart")
    assert response.status_code == 404
