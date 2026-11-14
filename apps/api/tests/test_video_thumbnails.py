import datetime as dt

from app.models.asset import Asset
from app.models.enums import AssetType, PipelineStage
from app.models.video import Video


def _video(client, db_session, topic, stage=PipelineStage.COMPLETED):
    project_id = client.post("/projects", json={"name": f"P {topic}"}).json()["id"]
    video = Video(
        project_id=project_id,
        topic=topic,
        target_duration_seconds=60,
        stage=stage,
        storyboard_approved=True,
    )
    db_session.add(video)
    db_session.flush()
    return video


def test_video_list_includes_the_first_thumbnail_url(client, db_session):
    video = _video(client, db_session, "with thumbs")
    now = dt.datetime.now(dt.UTC)
    for i, label in enumerate("ABC"):
        db_session.add(
            Asset(
                video_id=video.id,
                asset_type=AssetType.THUMBNAIL,
                path=f"/data/{video.id}/thumb_{label}.jpg",
                label=label,
                created_at=now + dt.timedelta(seconds=i),
            )
        )
    db_session.flush()

    listed = next(v for v in client.get("/videos").json() if v["id"] == str(video.id))
    assert listed["thumbnail_url"].endswith("thumb_A.jpg")  # the first one, same as before


def test_video_list_thumbnail_is_null_without_a_thumbnail_asset(client, db_session):
    video = _video(client, db_session, "no thumbs", stage=PipelineStage.SCRIPT)
    db_session.add(
        Asset(video_id=video.id, asset_type=AssetType.SCRIPT, path="/data/script.json", label="s")
    )
    db_session.flush()

    listed = next(v for v in client.get("/videos").json() if v["id"] == str(video.id))
    assert listed["thumbnail_url"] is None


def test_video_list_does_not_leak_the_raw_thumbnail_path(client, db_session):
    video = _video(client, db_session, "leak check")
    db_session.add(
        Asset(video_id=video.id, asset_type=AssetType.THUMBNAIL, path="/data/t.jpg", label="A")
    )
    db_session.flush()

    listed = next(v for v in client.get("/videos").json() if v["id"] == str(video.id))
    assert "thumbnail_path" not in listed


def test_single_video_endpoint_still_works(client, db_session):
    video = _video(client, db_session, "single")
    response = client.get(f"/videos/{video.id}")
    assert response.status_code == 200
    assert response.json()["thumbnail_url"] is None


def test_video_list_uses_one_query_for_all_thumbnails(client, db_session):
    videos = [_video(client, db_session, f"v{i}") for i in range(5)]
    for v in videos:
        db_session.add(
            Asset(video_id=v.id, asset_type=AssetType.THUMBNAIL, path=f"/d/{v.id}.jpg", label="A")
        )
    db_session.flush()

    from sqlalchemy import event

    asset_queries = []

    def count(conn, cursor, statement, *_args):
        if "FROM assets" in statement:
            asset_queries.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", count)
    try:
        listed = client.get("/videos").json()
    finally:
        event.remove(engine, "before_cursor_execute", count)

    assert len(listed) >= 5
    assert len(asset_queries) == 1  # not one per video
