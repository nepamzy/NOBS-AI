import json

import pytest

from services.common.errors import EngineNotConfiguredError
from services.connectors.youtube.adapter import YouTubeConnector


def test_raises_when_not_configured():
    connector = YouTubeConnector(client_id="", client_secret="", refresh_token="")
    with pytest.raises(EngineNotConfiguredError):
        connector.upload_video("video.mp4", "Title", "Description")


def test_upload_always_sends_private_and_proper_json(monkeypatch, tmp_path):
    video_file = tmp_path / "video.mp4"
    video_file.write_bytes(b"fake mp4 bytes")

    calls = []

    class _TokenResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "access-123"}

    class _UploadResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "id": "yt_video_1",
                "snippet": {"title": 'A "quoted" title'},
                "status": {"privacyStatus": "private"},
            }

    def fake_post(url, headers=None, data=None, files=None, timeout=None, **kwargs):
        calls.append({"url": url, "headers": headers, "files": files})
        if url == "https://oauth2.googleapis.com/token":
            return _TokenResponse()
        return _UploadResponse()

    import services.connectors.youtube.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    connector = YouTubeConnector(
        client_id="client-id", client_secret="client-secret", refresh_token="refresh-token"
    )
    result = connector.upload_video(
        str(video_file),
        'A "quoted" title',
        "Some description",
        tags=["story", "lesson"],
    )

    assert result.video_id == "yt_video_1"
    assert result.privacy_status == "private"

    token_call, upload_call = calls
    assert upload_call["url"].startswith(
        "https://www.googleapis.com/upload/youtube/v3/videos"
    )
    metadata_field = upload_call["files"]["metadata"]
    # Must be valid JSON even with a quote character in the title — the
    # earlier buggy version hand-concatenated the title into a JSON string.
    metadata = json.loads(metadata_field[1])
    assert metadata["snippet"]["title"] == 'A "quoted" title'
    assert metadata["snippet"]["description"] == "Some description"
    assert metadata["snippet"]["tags"] == ["story", "lesson"]
    assert metadata["status"]["privacyStatus"] == "private"
    assert "publishAt" not in metadata["status"]


def test_upload_video_has_no_way_to_request_public():
    import inspect

    from services.connectors.youtube.adapter import YouTubeConnector

    params = inspect.signature(YouTubeConnector.upload_video).parameters
    assert "privacy_status" not in params
    assert "scheduled_publish_at" not in params


def test_publish_video_flips_to_public(monkeypatch):
    calls = []

    class _TokenResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "access-123"}

    class _PublishResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "yt_video_1", "status": {"privacyStatus": "public"}}

    def fake_post(url, headers=None, data=None, timeout=None, **kwargs):
        return _TokenResponse()

    def fake_put(url, params=None, headers=None, json=None, timeout=None):
        calls.append({"url": url, "json": json})
        return _PublishResponse()

    import services.connectors.youtube.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)
    monkeypatch.setattr(adapter_module.httpx, "put", fake_put)

    connector = YouTubeConnector(
        client_id="client-id", client_secret="client-secret", refresh_token="refresh-token"
    )
    result = connector.publish_video("yt_video_1")

    assert result["status"]["privacyStatus"] == "public"
    assert calls[0]["json"]["status"]["privacyStatus"] == "public"
