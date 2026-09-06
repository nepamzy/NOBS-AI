def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_project_and_video_enqueues_job(client):
    project_resp = client.post("/projects", json={"name": "My Project"})
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    video_resp = client.post(
        "/videos",
        json={
            "project_id": project_id,
            "topic": "test topic",
            "target_duration_seconds": 60,
            "run_research": True,
        },
    )
    assert video_resp.status_code == 201
    body = video_resp.json()
    assert body["stage"] == "topic"
    assert body["project_id"] == project_id

    assert len(client.enqueued_jobs) == 1
    assert client.enqueued_jobs[0]["run_research"] is True


def test_list_videos_filters_by_project(client):
    project_a = client.post("/projects", json={"name": "A"}).json()["id"]
    project_b = client.post("/projects", json={"name": "B"}).json()["id"]
    client.post(
        "/videos", json={"project_id": project_a, "topic": "a1", "target_duration_seconds": 60}
    )
    client.post(
        "/videos", json={"project_id": project_b, "topic": "b1", "target_duration_seconds": 60}
    )

    response = client.get("/videos", params={"project_id": project_a})
    assert response.status_code == 200
    videos = response.json()
    assert len(videos) == 1
    assert videos[0]["topic"] == "a1"


def test_create_video_for_missing_project_404s(client):
    response = client.post(
        "/videos",
        json={
            "project_id": "00000000-0000-0000-0000-000000000000",
            "topic": "x",
            "target_duration_seconds": 60,
        },
    )
    assert response.status_code == 404


def test_approve_storyboard_rejects_wrong_stage(client):
    project_id = client.post("/projects", json={"name": "p"}).json()["id"]
    video_id = client.post(
        "/videos",
        json={"project_id": project_id, "topic": "t", "target_duration_seconds": 60},
    ).json()["id"]

    response = client.post(f"/videos/{video_id}/approve-storyboard")
    assert response.status_code == 409


def _make_video_with_script(client, db_session):
    import uuid

    from app.models.script import Scene, Script

    project_id = client.post("/projects", json={"name": "p"}).json()["id"]
    video_id = client.post(
        "/videos",
        json={"project_id": project_id, "topic": "t", "target_duration_seconds": 60},
    ).json()["id"]

    script = Script(
        video_id=uuid.UUID(video_id),
        title="t",
        hook="h",
        estimated_duration_seconds=60,
        word_count=10,
    )
    script.scenes = [Scene(order=1, narration="original", visual_prompt="v", duration_seconds=8)]
    db_session.add(script)
    db_session.flush()
    return video_id, script.scenes[0].id


def test_update_scene_edits_narration(client, db_session):
    video_id, scene_id = _make_video_with_script(client, db_session)

    response = client.patch(
        f"/videos/{video_id}/scenes/{scene_id}", json={"narration": "revised narration"}
    )
    assert response.status_code == 200
    assert response.json()["narration"] == "revised narration"


def test_update_scene_rejected_after_storyboard_approved(client, db_session):
    from app.models.video import Video

    video_id, scene_id = _make_video_with_script(client, db_session)
    video = db_session.get(Video, video_id)
    video.storyboard_approved = True
    db_session.flush()

    response = client.patch(f"/videos/{video_id}/scenes/{scene_id}", json={"narration": "x"})
    assert response.status_code == 409


def test_regenerate_scene_blocked_without_llm_config(client, db_session):
    video_id, scene_id = _make_video_with_script(client, db_session)

    response = client.post(f"/videos/{video_id}/scenes/{scene_id}/regenerate")
    assert response.status_code == 402
    assert "PAYMENT / COST WARNING" in response.json()["detail"]


def test_regenerate_scene_rejected_after_storyboard_approved(client, db_session):
    from app.models.video import Video

    video_id, scene_id = _make_video_with_script(client, db_session)
    video = db_session.get(Video, video_id)
    video.storyboard_approved = True
    db_session.flush()

    response = client.post(f"/videos/{video_id}/scenes/{scene_id}/regenerate")
    assert response.status_code == 409


def test_list_assets_empty_for_new_video(client, db_session):
    video_id, _ = _make_video_with_script(client, db_session)

    response = client.get(f"/videos/{video_id}/assets")
    assert response.status_code == 200
    assert response.json() == []
