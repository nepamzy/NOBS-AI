def test_upload_source_video_creates_row_and_enqueues_job(client, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "local_storage_root", str(tmp_path))

    response = client.post(
        "/source-videos",
        files={"file": ("my-podcast.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "my-podcast.mp4"
    assert body["stage"] == "uploaded"
    assert body["auto_publish"] is True  # defaults True for this feature specifically
    assert len(client.enqueued_clip_jobs) == 1


def test_upload_rejects_unsupported_content_type(client):
    response = client.post(
        "/source-videos",
        files={"file": ("notes.txt", b"not a video", "text/plain")},
    )
    assert response.status_code == 400


def test_list_and_get_source_video(client, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "local_storage_root", str(tmp_path))

    create_response = client.post(
        "/source-videos", files={"file": ("video.mp4", b"bytes", "video/mp4")}
    )
    video_id = create_response.json()["id"]

    list_response = client.get("/source-videos")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/source-videos/{video_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == video_id


def test_toggle_auto_publish(client, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "local_storage_root", str(tmp_path))

    create_response = client.post(
        "/source-videos", files={"file": ("video.mp4", b"bytes", "video/mp4")}
    )
    video_id = create_response.json()["id"]
    assert create_response.json()["auto_publish"] is True

    response = client.patch(f"/source-videos/{video_id}", json={"auto_publish": False})
    assert response.status_code == 200
    assert response.json()["auto_publish"] is False


def test_other_users_source_video_is_404(client, db_session, tmp_path):
    from app.auth.security import hash_password
    from app.models.enums import UserRole
    from app.models.source_video import SourceVideo
    from app.models.user import User

    other_owner = User(
        email="other@local", display_name="Other", password_hash=hash_password("x"),
        role=UserRole.USER,
    )
    db_session.add(other_owner)
    db_session.flush()
    other_video = SourceVideo(
        owner_id=other_owner.id, original_filename="x.mp4", source_path=str(tmp_path / "x.mp4")
    )
    db_session.add(other_video)
    db_session.flush()

    response = client.get(f"/source-videos/{other_video.id}")
    assert response.status_code == 404


def test_publish_clip_requires_finished_render(client, db_session, tmp_path):
    from app.models.clip import Clip
    from app.models.source_video import SourceVideo

    source_video = SourceVideo(
        owner_id=client.admin_user.id,
        original_filename="video.mp4",
        source_path=str(tmp_path / "video.mp4"),
    )
    db_session.add(source_video)
    db_session.flush()
    clip = Clip(
        source_video_id=source_video.id, start_seconds=0.0, end_seconds=10.0, title="Clip"
    )
    db_session.add(clip)
    db_session.flush()

    response = client.post(f"/clips/{clip.id}/publish")
    assert response.status_code == 409


def test_publish_clip_returns_402_when_second_channel_not_configured(client, db_session, tmp_path):
    from app.models.clip import Clip
    from app.models.source_video import SourceVideo

    source_video = SourceVideo(
        owner_id=client.admin_user.id,
        original_filename="video.mp4",
        source_path=str(tmp_path / "video.mp4"),
    )
    db_session.add(source_video)
    db_session.flush()
    clip = Clip(
        source_video_id=source_video.id,
        start_seconds=0.0,
        end_seconds=10.0,
        title="Clip",
        clip_path=str(tmp_path / "clip.mp4"),
    )
    db_session.add(clip)
    db_session.flush()

    response = client.post(f"/clips/{clip.id}/publish")
    assert response.status_code == 402
