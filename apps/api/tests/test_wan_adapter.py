import pytest

from services.common.errors import ApprovalRequiredError
from services.video.engine import SceneClipRequest
from services.video.wan.adapter import WanEngine


def test_raises_when_not_configured():
    engine = WanEngine(runpod_api_key="", wan_endpoint_id="")
    request = SceneClipRequest(scene_id="s1", visual_prompt="a cat", duration_seconds=8)
    with pytest.raises(ApprovalRequiredError):
        engine.generate_clip(request, "/tmp/does-not-matter.mp4")


def test_submits_polls_and_downloads_the_finished_clip(tmp_path, monkeypatch):
    posts = []
    gets = []

    class _FakeSubmitResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "job123", "status": "IN_QUEUE"}

    class _FakeStatusResponse:
        def __init__(self, status):
            self._status = status

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "status": self._status,
                "output": {"clip_url": "https://cdn.example/clip.mp4", "duration_seconds": 8.0},
            }

    class _FakeClipDownload:
        def raise_for_status(self):
            pass

        content = b"fake clip bytes"

    status_sequence = iter(["IN_PROGRESS", "COMPLETED"])

    def fake_post(url, headers=None, json=None, timeout=None):
        posts.append({"url": url, "headers": headers, "json": json})
        return _FakeSubmitResponse()

    def fake_get(url, headers=None, timeout=None):
        if url == "https://cdn.example/clip.mp4":
            return _FakeClipDownload()
        gets.append(url)
        return _FakeStatusResponse(next(status_sequence))

    import services.video.wan.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)
    monkeypatch.setattr(adapter_module.httpx, "get", fake_get)
    monkeypatch.setattr(adapter_module.time, "sleep", lambda _seconds: None)

    output_path = str(tmp_path / "clip.mp4")
    engine = WanEngine(runpod_api_key="key", wan_endpoint_id="endpoint123")
    request = SceneClipRequest(scene_id="s1", visual_prompt="a cat", duration_seconds=8)
    result = engine.generate_clip(request, output_path)

    assert posts[0]["url"] == "https://api.runpod.ai/v2/endpoint123/run"
    assert posts[0]["headers"]["Authorization"] == "Bearer key"
    assert posts[0]["json"] == {"input": {"prompt": "a cat", "duration_seconds": 8}}
    assert gets == [
        "https://api.runpod.ai/v2/endpoint123/status/job123",
        "https://api.runpod.ai/v2/endpoint123/status/job123",
    ]

    assert result.clip_path == output_path
    assert result.duration_seconds == 8.0
    with open(output_path, "rb") as f:
        assert f.read() == b"fake clip bytes"


def test_raises_when_job_fails(monkeypatch):
    class _FakeSubmitResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "job123", "status": "IN_QUEUE"}

    class _FakeStatusResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "FAILED", "output": None}

    import services.video.wan.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", lambda *a, **k: _FakeSubmitResponse())
    monkeypatch.setattr(adapter_module.httpx, "get", lambda *a, **k: _FakeStatusResponse())

    engine = WanEngine(runpod_api_key="key", wan_endpoint_id="endpoint123")
    request = SceneClipRequest(scene_id="s1", visual_prompt="a cat", duration_seconds=8)
    with pytest.raises(RuntimeError, match="FAILED"):
        engine.generate_clip(request, "/tmp/does-not-matter.mp4")
