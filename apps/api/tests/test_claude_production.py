"""Choosing Claude as the producer, handing the approved brief over the
connector, getting the finished video back, and scheduling/publishing it —
including the worker's due-time publisher."""

import json
import subprocess
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from app import publishing
from app.config import settings
from app.connector import importer
from app.models.asset import Asset
from app.models.enums import PipelineStage
from app.models.project import Project
from app.models.script import Scene, Script
from app.models.video import Video

from services.ai.orchestration.pipeline import PipelineBlocked, PipelineContext, advance_one_stage
from services.ai.research.engine import ResearchEngine
from services.ai.script.engine import ScriptEngine
from services.scheduling.publish_scheduler import publish_due_videos
from services.video.wan.adapter import WanEngine
from services.voice.chatterbox.adapter import ChatterboxEngine


@pytest.fixture(scope="session")
def tiny_mp4(tmp_path_factory) -> bytes:
    path = tmp_path_factory.mktemp("media2") / "tiny.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=160x120:rate=10",
         "-pix_fmt", "yuv420p", str(path)],
        check=True, capture_output=True,
    )
    return path.read_bytes()


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "local_storage_root", str(tmp_path / "store"))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "google_youtube_client_id", "id")
    monkeypatch.setattr(settings, "google_youtube_client_secret", "secret")
    monkeypatch.setattr(settings, "google_youtube_refresh_token", "refresh")


@pytest.fixture
def youtube(monkeypatch):
    calls = SimpleNamespace(uploads=[], publishes=[], fail_publish=False)

    class Fake:
        def upload_video(self, path, title, description, tags):
            calls.uploads.append((path, title, description))
            return SimpleNamespace(video_id="yt-abc")

        def publish_video(self, video_id):
            if calls.fail_publish:
                from services.common.errors import EngineNotConfiguredError

                raise EngineNotConfiguredError("YouTube said no")
            calls.publishes.append(video_id)

    monkeypatch.setattr(publishing, "_youtube", lambda: Fake())
    return calls


@pytest.fixture
def serve(monkeypatch):
    table: dict[str, httpx.Response] = {}
    monkeypatch.setattr(
        importer, "_http_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(lambda r: table.get(str(r.url), httpx.Response(404))),
            follow_redirects=False,
        ),
    )
    monkeypatch.setattr(importer, "_assert_public_https", lambda url: None)
    return table


def _key(client) -> str:
    return client.post("/connector/keys", json={"name": "t"}).json()["key"]


def _call(client, key, name, arguments):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}}
    response = client.post(f"/mcp/{key}", json=body)
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    return result["isError"], result["content"][0]["text"]


def _video(db, client, *, stage, producer="runpod", final=None, owner=None) -> Video:
    owner = owner or client.admin_user
    project = Project(owner_id=owner.id, name="P")
    db.add(project)
    db.flush()
    video = Video(
        project_id=project.id, topic="Five mistakes", target_duration_seconds=60,
        voice_preset="warm-narrator", style_preset="", stage=stage, producer=producer,
        storyboard_approved=True, final_video_path=final,
    )
    db.add(video)
    db.flush()
    script = Script(
        video_id=video.id, title="Five mistakes", hook="Stop doing these.",
        estimated_duration_seconds=20, word_count=8, approved=True,
    )
    script.scenes = [
        Scene(order=1, narration="Mistake one is skipping tests.",
              visual_prompt="a dev at a desk", duration_seconds=10),
        Scene(order=2, narration="Mistake two is no git.", visual_prompt="terminal",
              duration_seconds=10),
    ]
    db.add(script)
    db.flush()
    return video


def _ctx() -> PipelineContext:
    return PipelineContext(
        research_engine=ResearchEngine(llm_provider="", llm_api_key=""),
        script_engine=ScriptEngine(llm_provider="", llm_api_key=""),
        voice_engine=ChatterboxEngine(api_url=""),
        video_engine=WanEngine(runpod_api_key="", wan_endpoint_id=""),
        storage_root="./storage/local",
    )


# ---- producer choice in the pipeline -------------------------------------


def test_claude_producer_parks_after_compliance_without_touching_voice_or_gpu(db_session, client):
    video = _video(db_session, client, stage=PipelineStage.COMPLIANCE_CHECK, producer="claude")
    advance_one_stage(video, db_session, _ctx(), run_research=False)
    assert video.stage == PipelineStage.AWAITING_CLAUDE

    with pytest.raises(PipelineBlocked) as blocked:
        advance_one_stage(video, db_session, _ctx(), run_research=False)
    assert blocked.value.stage == "awaiting_claude"
    assert video.stage == PipelineStage.AWAITING_CLAUDE  # stays parked, not failed


def test_runpod_producer_still_goes_to_voice(db_session, client):
    video = _video(db_session, client, stage=PipelineStage.COMPLIANCE_CHECK, producer="runpod")
    advance_one_stage(video, db_session, _ctx(), run_research=False)
    assert video.stage == PipelineStage.VOICE


def test_create_video_accepts_producer_and_defaults_to_runpod(client):
    project = client.post("/projects", json={"name": "P"}).json()["id"]
    base = {
        "project_id": project, "topic": "t", "target_duration_seconds": 60,
        "own_scenes": [{"narration": "hello world", "visual_prompt": "x", "duration_seconds": 5}],
    }
    assert client.post("/videos", json=base).json()["producer"] == "runpod"
    claude = client.post("/videos", json={**base, "producer": "claude"})
    assert claude.status_code == 201 and claude.json()["producer"] == "claude"
    assert client.post("/videos", json={**base, "producer": "nobody"}).status_code == 422


# ---- Claude picks up and completes a job ---------------------------------


def test_claude_job_brief_then_complete(client, db_session, env, serve, tiny_mp4):
    key = _key(client)
    video = _video(db_session, client, stage=PipelineStage.AWAITING_CLAUDE, producer="claude")
    serve["https://f.test/v.mp4"] = httpx.Response(200, content=tiny_mp4)

    error, text = _call(client, key, "nobs_list_claude_jobs", {})
    assert not error and str(video.id) in text

    error, text = _call(client, key, "nobs_get_claude_job", {"video_id": str(video.id)})
    brief = json.loads(text)
    assert not error
    assert [s["narration"] for s in brief["scenes"]] == [
        "Mistake one is skipping tests.", "Mistake two is no git.",
    ]
    assert brief["voice"]["name"] == "Warm Narrator"
    assert brief["youtube"]["suggested_title"] == "Five mistakes"

    error, text = _call(
        client, key, "nobs_complete_claude_job",
        {"video_id": str(video.id), "video_url": "https://f.test/v.mp4"},
    )
    assert not error, text
    db_session.refresh(video)
    assert video.stage == PipelineStage.COMPLETED and video.stage_progress_percent == 100
    assert video.youtube_published is False
    assert db_session.query(Asset).filter(Asset.video_id == video.id).count() >= 2

    # No longer a pending job, and can't be completed twice.
    assert json.loads(_call(client, key, "nobs_list_claude_jobs", {})[1]) == []
    assert _call(
        client, key, "nobs_complete_claude_job",
        {"video_id": str(video.id), "video_url": "https://f.test/v.mp4"},
    )[0] is True


def test_claude_cannot_touch_other_users_or_non_claude_jobs(client, db_session, env, serve):
    from app.auth.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    key = _key(client)
    other = User(email="o@local", display_name="O", password_hash=hash_password("pw-12345678"),
                 role=UserRole.USER)
    db_session.add(other)
    db_session.flush()
    theirs = _video(db_session, client, stage=PipelineStage.AWAITING_CLAUDE, producer="claude",
                    owner=other)
    runpod = _video(db_session, client, stage=PipelineStage.AWAITING_CLAUDE, producer="runpod")

    assert _call(client, key, "nobs_get_claude_job", {"video_id": str(theirs.id)})[0] is True
    assert _call(client, key, "nobs_get_claude_job", {"video_id": str(runpod.id)})[0] is True
    assert json.loads(_call(client, key, "nobs_list_claude_jobs", {})[1]) == []


def test_direct_upload_can_finish_a_claude_job(client, db_session, env, tiny_mp4):
    key = _key(client)
    video = _video(db_session, client, stage=PipelineStage.AWAITING_CLAUDE, producer="claude")
    response = client.post(
        f"/connector/upload/{key}", data={"video_id": str(video.id)},
        files={"file": ("v.mp4", tiny_mp4, "video/mp4")},
    )
    assert response.status_code == 200, response.text
    db_session.refresh(video)
    assert video.stage == PipelineStage.COMPLETED


# ---- scheduling ------------------------------------------------------------


def _future(**kw) -> str:
    return (datetime.now(UTC) + timedelta(**kw)).isoformat()


def test_schedule_publish_rest_rules(client, db_session, env):
    done = _video(db_session, client, stage=PipelineStage.COMPLETED, final="x/final.mp4")
    url = f"/videos/{done.id}/schedule-publish"

    assert client.post(url, json={"publish_at": "2099-01-01T10:00:00"}).status_code == 422  # no tz
    assert client.post(url, json={"publish_at": _future(hours=-1)}).status_code == 422  # past
    assert client.post(url, json={"publish_at": _future(seconds=30)}).status_code == 422  # too soon

    ok = client.post(url, json={"publish_at": "2099-01-01T10:00:00+02:00", "title": "My title"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["scheduled_publish_at"].startswith("2099-01-01T08:00:00")  # stored as UTC
    db_session.refresh(done)
    assert done.youtube_title == "My title" and done.youtube_description == "Stop doing these."

    cancelled = client.delete(url)
    assert cancelled.status_code == 200 and cancelled.json()["scheduled_publish_at"] is None


def test_schedule_publish_needs_finished_video_and_youtube(client, db_session, env, monkeypatch):
    running = _video(db_session, client, stage=PipelineStage.VIDEO_GENERATION)
    body = {"publish_at": _future(days=1)}
    assert client.post(f"/videos/{running.id}/schedule-publish", json=body).status_code == 409

    done = _video(db_session, client, stage=PipelineStage.COMPLETED, final="x/final.mp4")
    monkeypatch.setattr(settings, "google_youtube_refresh_token", "")
    assert client.post(f"/videos/{done.id}/schedule-publish", json=body).status_code == 402


def test_worker_publishes_due_videos_and_leaves_future_ones(client, db_session, env, youtube):
    due = _video(db_session, client, stage=PipelineStage.COMPLETED, final="x/due.mp4")
    later = _video(db_session, client, stage=PipelineStage.COMPLETED, final="x/later.mp4")
    due.scheduled_publish_at = datetime.now(UTC) - timedelta(minutes=1)
    due.youtube_title, due.youtube_description = "Due title", "Due desc"
    later.scheduled_publish_at = datetime.now(UTC) + timedelta(days=1)
    db_session.flush()

    results = publish_due_videos(db_session)

    assert len(results) == 1 and "published on schedule" in results[0]
    assert youtube.uploads == [("x/due.mp4", "Due title", "Due desc")]
    assert youtube.publishes == ["yt-abc"]
    db_session.refresh(due)
    db_session.refresh(later)
    assert due.youtube_published is True and due.scheduled_publish_at is None
    assert later.youtube_published is False and later.scheduled_publish_at is not None


def test_failed_scheduled_publish_is_recorded_and_not_retried_forever(
    client, db_session, env, youtube
):
    video = _video(db_session, client, stage=PipelineStage.COMPLETED, final="x/f.mp4")
    video.scheduled_publish_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.flush()
    youtube.fail_publish = True

    assert "failed" in publish_due_videos(db_session)[0]
    db_session.refresh(video)
    assert video.youtube_published is False
    assert video.scheduled_publish_at is None  # won't fire again every minute
    assert "YouTube said no" in video.publish_error
    assert video.youtube_video_id == "yt-abc"  # the private upload was kept
    assert publish_due_videos(db_session) == []


# ---- Claude's publish / schedule tools ------------------------------------


def test_publish_tool_requires_explicit_confirm(client, db_session, env, youtube):
    key = _key(client)
    video = _video(db_session, client, stage=PipelineStage.COMPLETED, final="x/f.mp4")

    error, text = _call(client, key, "nobs_publish_video", {"video_id": str(video.id)})
    assert error and "confirm" in text and youtube.publishes == []

    error, text = _call(
        client, key, "nobs_publish_video", {"video_id": str(video.id), "confirm": True}
    )
    assert not error, text
    db_session.refresh(video)
    assert video.youtube_published is True and youtube.publishes == ["yt-abc"]


def test_schedule_tool_converts_time_zone_and_rejects_bare_times(client, db_session, env):
    key = _key(client)
    video = _video(db_session, client, stage=PipelineStage.COMPLETED, final="x/f.mp4")

    error, text = _call(
        client, key, "nobs_schedule_publish",
        {"video_id": str(video.id), "publish_at": "2099-06-01T17:00:00"},
    )
    assert error and "time zone" in text

    error, text = _call(
        client, key, "nobs_schedule_publish",
        {"video_id": str(video.id), "publish_at": "2099-06-01T17:00:00+01:00"},
    )
    assert not error, text
    assert json.loads(text)["scheduled_publish_at"].startswith("2099-06-01T16:00:00")

    error, text = _call(client, key, "nobs_cancel_scheduled_publish", {"video_id": str(video.id)})
    assert not error and json.loads(text)["scheduled_publish_at"] is None


def test_google_http_errors_become_plain_messages(client, db_session, env, monkeypatch):
    video = _video(db_session, client, stage=PipelineStage.COMPLETED, final="x/f.mp4")

    class Rejecting:
        def upload_video(self, *a):
            response = httpx.Response(401, request=httpx.Request("POST", "https://oauth2.test"))
            raise httpx.HTTPStatusError("nope", request=response.request, response=response)

    monkeypatch.setattr(publishing, "_youtube", lambda: Rejecting())
    with pytest.raises(publishing.PublishingError) as caught:
        publishing.publish_now(db_session, video)
    assert "HTTP 401" in str(caught.value) and "Channel Connections" in str(caught.value)
    assert "HTTPStatusError" not in str(caught.value)
    assert caught.value.status == 502
