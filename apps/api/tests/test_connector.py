"""The Claude connector: key lifecycle, the MCP endpoint, importing a finished
video (by link and by direct upload), and the guards around all of it. Uses a
real (tiny) MP4 made with ffmpeg, so probing/thumbnail extraction run for real.
"""

import subprocess
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from app.config import settings
from app.connector import importer
from app.connector.importer import ConnectorImportError
from app.models.asset import Asset
from app.models.enums import AssetType, PipelineStage
from app.models.project import Project
from app.models.script import Script
from app.models.video import Video


@pytest.fixture(scope="session")
def tiny_mp4(tmp_path_factory) -> bytes:
    path = tmp_path_factory.mktemp("media") / "tiny.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=4:size=160x120:rate=10",
            "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path.read_bytes()


@pytest.fixture
def stored(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "local_storage_root", str(tmp_path / "store"))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "api_base_url", "https://api.example.test")
    monkeypatch.setattr(settings, "landing_base_url", "https://app.example.test")
    return tmp_path / "store"


@pytest.fixture
def serve(monkeypatch):
    """Makes importer downloads come from an in-memory table of url -> response
    (no network), and skips the DNS/public-address check that needs real DNS."""
    table: dict[str, httpx.Response] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return table.get(str(request.url), httpx.Response(404))

    monkeypatch.setattr(
        importer, "_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False),
    )
    monkeypatch.setattr(importer, "_assert_public_https", lambda url: None)
    return table


def _make_key(client, name="Claude session") -> dict:
    response = client.post("/connector/keys", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def _rpc(client, key, method, params=None, msg_id=1):
    body = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        body["params"] = params
    return client.post(f"/mcp/{key}", json=body)


def _call(client, key, name, arguments):
    response = _rpc(client, key, "tools/call", {"name": name, "arguments": arguments})
    assert response.status_code == 200, response.text
    return response.json()["result"]


# ---- keys -----------------------------------------------------------------


def test_create_list_and_revoke_key(client):
    created = _make_key(client)
    assert created["key"].startswith("nobs_ck_")
    assert created["connector_url"].endswith(f"/mcp/{created['key']}")

    listed = client.get("/connector/keys").json()
    assert len(listed) == 1
    assert "key" not in listed[0]  # the secret is never shown again
    assert created["key"] not in str(listed)

    assert client.delete(f"/connector/keys/{created['id']}").status_code == 204
    assert client.get("/connector/keys").json()[0]["revoked"] is True
    assert _rpc(client, created["key"], "ping").status_code == 401


def test_only_admin_can_create_keys(client, db_session):
    from app.auth.security import generate_session_token, hash_lookup_value, hash_password
    from app.main import app
    from app.models.auth import AuthSession
    from app.models.enums import UserRole
    from app.models.user import User
    from fastapi.testclient import TestClient

    guest = User(
        email="guest@local", display_name="Guest",
        password_hash=hash_password("pw-guest-123"), role=UserRole.USER,
    )
    db_session.add(guest)
    db_session.flush()
    token = generate_session_token()
    db_session.add(
        AuthSession(
            user_id=guest.id, token_hash=hash_lookup_value(token),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    db_session.flush()

    guest_client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
    assert guest_client.post("/connector/keys", json={"name": "x"}).status_code == 403


def test_bad_key_is_rejected(client):
    assert _rpc(client, "nobs_ck_not-a-real-key", "ping").status_code == 401
    assert _rpc(client, "something-else", "ping").status_code == 401


def test_bearer_header_works_too(client):
    key = _make_key(client)["key"]
    response = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert response.status_code == 200
    assert response.json()["result"] == {}


# ---- protocol --------------------------------------------------------------


def test_initialize_and_tools_list(client):
    key = _make_key(client)["key"]

    init = _rpc(client, key, "initialize", {"protocolVersion": "2025-06-18"}).json()["result"]
    assert init["protocolVersion"] == "2025-06-18"
    assert init["serverInfo"]["name"] == "nobs-ai"
    assert "tools" in init["capabilities"]

    tools = _rpc(client, key, "tools/list").json()["result"]["tools"]
    names = {t["name"] for t in tools}
    assert "nobs_import_video" in names
    # The connector must never be able to publish, upload to YouTube or delete.
    assert not any(bad in n for n in names for bad in ("publish", "youtube", "delete", "schedule"))
    assert all(t["inputSchema"]["type"] == "object" for t in tools)


def test_notification_gets_202_and_unknown_method_errors(client):
    key = _make_key(client)["key"]
    note = client.post(
        f"/mcp/{key}", json={"jsonrpc": "2.0", "method": "notifications/initialized"}
    )
    assert note.status_code == 202

    unknown = _rpc(client, key, "no/such/method").json()
    assert unknown["error"]["code"] == -32601


# ---- importing -------------------------------------------------------------


def test_import_by_link_creates_a_completed_project(client, db_session, serve, stored, tiny_mp4):
    key = _make_key(client)["key"]
    serve["https://files.example.test/v.mp4"] = httpx.Response(200, content=tiny_mp4)

    result = _call(
        client, key, "nobs_import_video",
        {
            "title": "5 mistakes new developers make",
            "video_url": "https://files.example.test/v.mp4",
            "project_name": "Dev tips",
            "description": "A short video.",
            "scenes": [
                {"narration": "Mistake one: skipping tests.", "duration_seconds": 2},
                {"narration": "Mistake two: no version control.", "duration_seconds": 2},
            ],
        },
    )
    assert result["isError"] is False, result
    import json

    summary = json.loads(result["content"][0]["text"])
    assert summary["stage"] == "completed"
    assert summary["published"] is False
    assert summary["uploaded_to_youtube"] is False
    assert summary["open_in_nobs_ai"].startswith("https://app.example.test/videos/")

    video = db_session.get(Video, summary["video_id"])
    assert video.stage == PipelineStage.COMPLETED
    assert video.stage_progress_percent == 100
    assert video.storyboard_approved is True
    assert video.youtube_video_id is None and video.youtube_published is False
    assert video.target_duration_seconds == 4
    assert video.project.name == "Dev tips"
    assert video.project.owner_id == client.admin_user.id

    script = db_session.query(Script).filter(Script.video_id == video.id).one()
    assert [s.order for s in script.scenes] == [1, 2]

    types = [
        a.asset_type
        for a in db_session.query(Asset).filter(Asset.video_id == video.id).order_by(Asset.label)
    ]
    assert types.count(AssetType.FINAL_VIDEO) == 1
    assert types.count(AssetType.THUMBNAIL) == 3  # A/B/C frames taken from the video

    # The file really was persisted somewhere that outlives the temp folder.
    assert (stored / str(video.id) / "final.mp4").stat().st_size == len(tiny_mp4)


def test_import_without_scenes_still_gets_a_script_and_reuses_the_project(
    client, db_session, serve, stored, tiny_mp4
):
    key = _make_key(client)["key"]
    serve["https://files.example.test/v.mp4"] = httpx.Response(200, content=tiny_mp4)
    args = {"title": "Take", "video_url": "https://files.example.test/v.mp4"}

    first = _call(client, key, "nobs_import_video", args)
    second = _call(client, key, "nobs_import_video", {**args, "title": "Take 2"})
    assert first["isError"] is False and second["isError"] is False

    projects = db_session.query(Project).filter(Project.name == importer.DEFAULT_PROJECT_NAME).all()
    assert len(projects) == 1
    assert db_session.query(Video).filter(Video.project_id == projects[0].id).count() == 2
    assert db_session.query(Script).count() == 2


def test_import_with_optional_files(client, db_session, serve, stored, tiny_mp4):
    key = _make_key(client)["key"]
    serve["https://files.example.test/v.mp4"] = httpx.Response(200, content=tiny_mp4)
    serve["https://files.example.test/vo.mp3"] = httpx.Response(200, content=b"ID3fake")
    srt = b"1\n00:00:00,000 --> 00:00:01,000\nHi\n"
    serve["https://files.example.test/c.srt"] = httpx.Response(200, content=srt)
    serve["https://files.example.test/t.png"] = httpx.Response(200, content=b"\x89PNGfake")

    result = _call(
        client, key, "nobs_import_video",
        {
            "title": "With extras",
            "video_url": "https://files.example.test/v.mp4",
            "voiceover_url": "https://files.example.test/vo.mp3",
            "captions_url": "https://files.example.test/c.srt",
            "thumbnail_url": "https://files.example.test/t.png",
        },
    )
    assert result["isError"] is False, result
    assets = db_session.query(Asset).all()
    kinds = sorted(a.asset_type.value for a in assets)
    assert kinds == ["captions", "final_video", "thumbnail", "voiceover"]  # one supplied thumbnail


@pytest.mark.parametrize(
    ("response", "expect"),
    [
        (httpx.Response(200, content=b"this is not a video"), "readable video"),
        (httpx.Response(404), "HTTP 404"),
    ],
)
def test_import_rejects_bad_files(client, serve, stored, response, expect):
    key = _make_key(client)["key"]
    serve["https://files.example.test/v.mp4"] = response
    result = _call(
        client, key, "nobs_import_video",
        {"title": "x", "video_url": "https://files.example.test/v.mp4"},
    )
    assert result["isError"] is True
    assert expect in result["content"][0]["text"]


def test_import_rejects_oversize_and_leaves_nothing_behind(
    client, db_session, serve, stored, tiny_mp4, monkeypatch
):
    key = _make_key(client)["key"]
    monkeypatch.setattr(settings, "connector_max_import_mb", 0)
    serve["https://files.example.test/v.mp4"] = httpx.Response(200, content=tiny_mp4)
    result = _call(
        client, key, "nobs_import_video",
        {"title": "x", "video_url": "https://files.example.test/v.mp4"},
    )
    assert result["isError"] is True
    assert "limit" in result["content"][0]["text"]
    assert db_session.query(Video).count() == 0


def test_import_needs_title_and_url(client):
    key = _make_key(client)["key"]
    assert _call(client, key, "nobs_import_video", {"title": "x"})["isError"] is True


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/v.mp4",  # not https
        "https://127.0.0.1/v.mp4",  # loopback
        "https://169.254.169.254/latest/meta-data",  # cloud metadata
        "https://10.0.0.5/v.mp4",  # private network
        "https://[::1]/v.mp4",
        "file:///etc/passwd",
    ],
)
def test_ssrf_guard_refuses_non_public_targets(url):
    with pytest.raises(ConnectorImportError):
        importer._assert_public_https(url)


# ---- reading back, and scoping --------------------------------------------


def test_list_and_get_video_are_scoped_to_the_key_owner(
    client, db_session, serve, stored, tiny_mp4
):
    import json

    from app.auth.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    key = _make_key(client)["key"]
    serve["https://files.example.test/v.mp4"] = httpx.Response(200, content=tiny_mp4)
    mine = json.loads(
        _call(client, key, "nobs_import_video",
              {"title": "Mine", "video_url": "https://files.example.test/v.mp4"})["content"][0]["text"]
    )

    other = User(
        email="other@local", display_name="Other",
        password_hash=hash_password("pw-other-123"), role=UserRole.USER,
    )
    db_session.add(other)
    db_session.flush()
    project = Project(owner_id=other.id, name="Theirs")
    db_session.add(project)
    db_session.flush()
    theirs = Video(
        project_id=project.id, topic="Not yours", target_duration_seconds=10,
        stage=PipelineStage.COMPLETED,
    )
    db_session.add(theirs)
    db_session.flush()

    listed = json.loads(_call(client, key, "nobs_list_videos", {})["content"][0]["text"])
    assert [v["video_id"] for v in listed] == [mine["video_id"]]

    ok = _call(client, key, "nobs_get_video", {"video_id": mine["video_id"]})
    assert ok["isError"] is False
    blocked = _call(client, key, "nobs_get_video", {"video_id": str(theirs.id)})
    assert blocked["isError"] is True

    projects = json.loads(_call(client, key, "nobs_list_projects", {})["content"][0]["text"])
    assert [p["name"] for p in projects] == [importer.DEFAULT_PROJECT_NAME]


def test_upload_instructions_use_the_configured_api_url(client, stored):
    key = _make_key(client)["key"]
    result = _call(client, key, "nobs_upload_instructions", {})
    assert f"https://api.example.test/connector/upload/{key}" in result["content"][0]["text"]


# ---- direct upload ---------------------------------------------------------


def test_direct_upload_imports_a_file(client, db_session, stored, tiny_mp4):
    key = _make_key(client)["key"]
    response = client.post(
        f"/connector/upload/{key}",
        data={"title": "From sandbox", "project_name": "Sandbox"},
        files={"file": ("video.mp4", tiny_mp4, "video/mp4")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stage"] == "completed"
    assert db_session.get(Video, body["video_id"]).project.name == "Sandbox"


def test_direct_upload_rejects_non_video_and_bad_key(client, stored, tiny_mp4):
    key = _make_key(client)["key"]
    bad = client.post(
        f"/connector/upload/{key}",
        data={"title": "x"},
        files={"file": ("video.mp4", b"not a video", "video/mp4")},
    )
    assert bad.status_code == 400

    nokey = client.post(
        "/connector/upload/nobs_ck_wrong",
        data={"title": "x"},
        files={"file": ("video.mp4", tiny_mp4, "video/mp4")},
    )
    assert nokey.status_code == 401


def test_access_log_never_contains_the_key():
    import logging

    from app.main import _RedactConnectorKeys

    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, "", 0,
        '%s - "%s %s HTTP/%s" %d',
        ("1.2.3.4:5", "POST", "/mcp/nobs_ck_SECRET-value_123", "1.1", 200),
        None,
    )
    assert _RedactConnectorKeys().filter(record) is True
    assert "SECRET" not in record.getMessage()
    assert "nobs_ck_[redacted]" in record.getMessage()
