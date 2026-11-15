"""Clips that Claude cuts and hands over: stored on the Clips page, uploaded to
YouTube PRIVATE, channel choice/fallback, publish only on explicit request, and
a failed YouTube step never losing the clip."""

import json
import subprocess
from types import SimpleNamespace

import httpx
import pytest
from app import publishing
from app.config import settings
from app.connector import importer
from app.models.clip import Clip
from app.models.source_video import SourceVideo

URL = "https://f.test/clip.mp4"


@pytest.fixture(scope="session")
def clip_mp4(tmp_path_factory) -> bytes:
    path = tmp_path_factory.mktemp("clipmedia") / "c.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
         "-pix_fmt", "yuv420p", str(path)],
        check=True, capture_output=True,
    )
    return path.read_bytes()


@pytest.fixture
def env(tmp_path, monkeypatch, clip_mp4):
    monkeypatch.setattr(settings, "local_storage_root", str(tmp_path / "store"))
    monkeypatch.setattr(settings, "storage_backend", "local")
    table = {URL: httpx.Response(200, content=clip_mp4)}
    monkeypatch.setattr(
        importer, "_http_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(lambda r: table.get(str(r.url), httpx.Response(404))),
            follow_redirects=False,
        ),
    )
    monkeypatch.setattr(importer, "_assert_public_https", lambda url: None)


def connect(monkeypatch, main=False, clips=False):
    for prefix, on in (("google_youtube", main), ("clips_youtube", clips)):
        for part in ("client_id", "client_secret", "refresh_token"):
            monkeypatch.setattr(settings, f"{prefix}_{part}", "x" if on else "")


@pytest.fixture
def youtube(monkeypatch):
    log = SimpleNamespace(uploads=[], publishes=[], fail_upload=False)

    def factory(channel):
        class Fake:
            def upload_video(self, path, title, description, tags):
                if log.fail_upload:
                    response = httpx.Response(
                        403, request=httpx.Request("POST", "https://oauth2.test")
                    )
                    raise httpx.HTTPStatusError("no", request=response.request, response=response)
                log.uploads.append((channel, title, description))
                return SimpleNamespace(video_id=f"yt-{channel}-{len(log.uploads)}")

            def publish_video(self, video_id):
                log.publishes.append((channel, video_id))

        return Fake()

    monkeypatch.setattr(publishing, "_youtube_for", factory)
    return log


def _key(client):
    return client.post("/connector/keys", json={"name": "t"}).json()["key"]


def _call(client, key, name, arguments):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}}
    result = client.post(f"/mcp/{key}", json=body).json()["result"]
    text = result["content"][0]["text"]
    try:
        return result["isError"], json.loads(text)
    except ValueError:
        return result["isError"], text


def _submit(client, key, **extra):
    return _call(client, key, "nobs_submit_clip",
                 {"title": "Best moment", "video_url": URL, "source_title": "Long talk", **extra})


def test_clip_goes_to_main_channel_privately_by_default(client, db_session, env, youtube,
                                                        monkeypatch):
    connect(monkeypatch, main=True, clips=True)
    error, out = _submit(client, _key(client), description="Why it works")
    assert not error, out
    assert out["youtube"] == {
        "uploaded": True, "channel": "main", "video_id": "yt-main-1",
        "url": "https://youtu.be/yt-main-1", "published": False,
    }
    assert youtube.uploads == [("main", "Best moment", "Why it works")]
    assert youtube.publishes == []  # private: nothing public without being told

    clip = db_session.query(Clip).one()
    assert clip.youtube_channel == "main" and clip.youtube_published is False
    assert clip.clip_path and (clip.end_seconds - clip.start_seconds) > 1.5


def test_falls_back_to_second_channel_when_main_not_connected(client, env, youtube, monkeypatch):
    connect(monkeypatch, main=False, clips=True)
    _, out = _submit(client, _key(client))
    assert out["youtube"]["channel"] == "clips" and youtube.uploads[0][0] == "clips"


def test_explicit_channel_is_never_silently_swapped(client, db_session, env, youtube, monkeypatch):
    connect(monkeypatch, main=False, clips=True)
    error, out = _submit(client, _key(client), channel="main")
    assert not error  # the clip itself was accepted...
    assert out["youtube"]["uploaded"] is False
    assert "main YouTube channel isn't connected" in out["youtube_error"]
    assert youtube.uploads == []
    assert db_session.query(Clip).count() == 1  # ...and is kept


def test_nothing_connected_keeps_the_clip_and_says_why(client, db_session, env, youtube,
                                                       monkeypatch):
    connect(monkeypatch)
    _, out = _submit(client, _key(client))
    assert out["youtube"]["uploaded"] is False
    assert "No YouTube channel is connected" in out["youtube_error"]
    assert "NOT uploaded" in out["next_step"]
    assert db_session.query(Clip).count() == 1


def test_clips_from_one_source_are_grouped(client, db_session, env, youtube, monkeypatch):
    connect(monkeypatch, main=True)
    key = _key(client)
    _submit(client, key)
    _submit(client, key, title="Second moment")
    assert db_session.query(SourceVideo).count() == 1
    assert db_session.query(Clip).count() == 2
    source = db_session.query(SourceVideo).one()
    assert source.original_filename == "Long talk" and source.auto_publish is False


def test_publish_only_when_asked_and_clip_stays_on_its_channel(client, db_session, env, youtube,
                                                               monkeypatch):
    key = _key(client)
    connect(monkeypatch, main=False, clips=True)
    _, out = _submit(client, key)  # lands privately on the second channel
    clip_id = out["clip_id"]

    connect(monkeypatch, main=True, clips=True)  # main gets connected later
    error, text = _call(client, key, "nobs_publish_clip", {"clip_id": clip_id})
    assert error and "confirm" in text and youtube.publishes == []

    error, out = _call(client, key, "nobs_publish_clip", {"clip_id": clip_id, "confirm": True})
    assert not error, out
    assert youtube.publishes == [("clips", "yt-clips-1")]  # not hopped to main
    assert out["youtube"]["published"] is True


def test_publish_true_on_submit_makes_it_public(client, env, youtube, monkeypatch):
    connect(monkeypatch, main=True)
    _, out = _submit(client, _key(client), publish=True)
    assert out["youtube"]["published"] is True and len(youtube.publishes) == 1


def test_youtube_failure_does_not_lose_the_clip(client, db_session, env, youtube, monkeypatch):
    connect(monkeypatch, main=True)
    youtube.fail_upload = True
    error, out = _submit(client, _key(client))
    assert not error
    assert "HTTP 403" in out["youtube_error"] and "HTTPStatusError" not in out["youtube_error"]
    clip = db_session.query(Clip).one()
    assert clip.clip_path and clip.youtube_video_id is None


def test_bad_input_is_rejected_without_storing(client, db_session, env, monkeypatch):
    key = _key(client)
    assert _submit(client, key, start_seconds=10, end_seconds=5)[0] is True
    assert _submit(client, key, start_seconds="abc")[0] is True
    assert _call(client, key, "nobs_submit_clip", {"title": "x"})[0] is True
    assert db_session.query(Clip).count() == 0


def test_list_clips_is_scoped_to_the_owner(client, db_session, env, youtube, monkeypatch):
    from app.auth.security import hash_password
    from app.models.enums import ClipJobStage, UserRole
    from app.models.user import User

    connect(monkeypatch, main=True)
    key = _key(client)
    _submit(client, key)
    other = User(email="o@local", display_name="O", password_hash=hash_password("pw-12345678"),
                 role=UserRole.USER)
    db_session.add(other)
    db_session.flush()
    theirs = SourceVideo(owner_id=other.id, original_filename="x", source_path="p",
                         stage=ClipJobStage.COMPLETED)
    db_session.add(theirs)
    db_session.flush()
    db_session.add(Clip(source_video_id=theirs.id, start_seconds=0, end_seconds=5, title="Theirs"))
    db_session.flush()

    _, listed = _call(client, key, "nobs_list_clips", {})
    assert [c["title"] for c in listed] == ["Best moment"]


def test_direct_clip_upload_endpoint(client, db_session, env, youtube, monkeypatch, clip_mp4):
    connect(monkeypatch, main=True)
    key = _key(client)
    response = client.post(
        f"/connector/upload-clip/{key}",
        data={"title": "From sandbox", "source_title": "Talk", "start_seconds": "12.5",
              "end_seconds": "14.5"},
        files={"file": ("c.mp4", clip_mp4, "video/mp4")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["youtube"]["channel"] == "main"
    clip = db_session.query(Clip).one()
    assert (clip.start_seconds, clip.end_seconds) == (12.5, 14.5)

    bad = client.post(f"/connector/upload-clip/{key}", data={"title": "x"},
                      files={"file": ("c.mp4", b"nope", "video/mp4")})
    assert bad.status_code == 400
    assert client.post("/connector/upload-clip/nobs_ck_wrong", data={"title": "x"},
                       files={"file": ("c.mp4", clip_mp4, "video/mp4")}).status_code == 401


def test_clips_page_publish_button_uses_the_clips_own_channel(client, db_session, env, youtube,
                                                              monkeypatch):
    connect(monkeypatch, main=True, clips=True)
    _, out = _submit(client, _key(client))  # uploaded privately to main
    response = client.post(f"/clips/{out['clip_id']}/publish")
    assert response.status_code == 200, response.text
    assert response.json()["youtube_channel"] == "main"
    assert youtube.publishes == [("main", "yt-main-1")]
