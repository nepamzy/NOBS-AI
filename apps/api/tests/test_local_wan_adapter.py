import pytest

from services.common.errors import ApprovalRequiredError
from services.video.engine import SceneClipRequest
from services.video.local_wan.adapter import LocalWanEngine


def test_raises_approval_required_when_not_configured():
    engine = LocalWanEngine(api_url="")
    request = SceneClipRequest(scene_id="s1", visual_prompt="a cat", duration_seconds=5)
    with pytest.raises(ApprovalRequiredError) as exc_info:
        engine.generate_clip(request, "/tmp/out.mp4")
    assert "LOCAL_WAN_API_URL" in exc_info.value.cost_warning.why_needed


def test_generate_clip_posts_prompt_and_writes_file(monkeypatch, tmp_path):
    calls = []

    class _FakeResponse:
        content = b"fake mp4 bytes"
        headers = {"x-clip-duration-seconds": "5.2"}

        def raise_for_status(self):
            pass

    def fake_post(url, json=None, timeout=None):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeResponse()

    import services.video.local_wan.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    engine = LocalWanEngine(api_url="http://192.168.1.50:8765")
    output_path = str(tmp_path / "clip.mp4")
    request = SceneClipRequest(
        scene_id="s1", visual_prompt="a cat on the grass", duration_seconds=5
    )

    result = engine.generate_clip(request, output_path)

    assert calls[0]["url"] == "http://192.168.1.50:8765/generate"
    assert calls[0]["json"] == {"prompt": "a cat on the grass", "duration_seconds": 5}
    assert result.clip_path == output_path
    assert result.duration_seconds == 5.2
    assert open(output_path, "rb").read() == b"fake mp4 bytes"
