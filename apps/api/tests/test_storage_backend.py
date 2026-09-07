import pytest

from services.common.errors import EngineNotConfiguredError
from services.storage.backend import LocalStorageBackend
from services.storage.factory import get_storage_backend
from services.storage.supabase_backend import SupabaseStorageBackend


def test_local_backend_returns_the_path_unchanged():
    backend = LocalStorageBackend()
    assert backend.upload("./storage/local/video/final.mp4", "video/final.mp4") == (
        "./storage/local/video/final.mp4"
    )


def test_factory_returns_local_backend_by_default():
    backend = get_storage_backend("local", "", "", "nobs-ai")
    assert isinstance(backend, LocalStorageBackend)


def test_factory_returns_supabase_backend_when_selected():
    backend = get_storage_backend(
        "supabase", "https://x.supabase.co", "service-role-key", "nobs-ai"
    )
    assert isinstance(backend, SupabaseStorageBackend)


def test_supabase_backend_raises_when_not_configured():
    backend = SupabaseStorageBackend(project_url="", service_role_key="", bucket="nobs-ai")
    with pytest.raises(EngineNotConfiguredError):
        backend.upload("/tmp/does-not-matter.mp4", "video/final.mp4")


def test_supabase_backend_uploads_and_returns_public_url(tmp_path, monkeypatch):
    local_file = tmp_path / "final.mp4"
    local_file.write_bytes(b"fake video bytes")

    calls = []

    class _FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers=None, content=None, timeout=None):
        calls.append({"url": url, "headers": headers, "content": content, "timeout": timeout})
        return _FakeResponse()

    import services.storage.supabase_backend as supabase_backend_module

    monkeypatch.setattr(supabase_backend_module.httpx, "post", fake_post)

    backend = SupabaseStorageBackend(
        project_url="https://flgpusbxipcotgiotdmv.supabase.co",
        service_role_key="service-role-key",
        bucket="nobs-ai",
    )
    url = backend.upload(str(local_file), "video123/final.mp4")

    assert url == (
        "https://flgpusbxipcotgiotdmv.supabase.co/storage/v1/object/public/nobs-ai/video123/final.mp4"
    )
    assert len(calls) == 1
    assert calls[0]["url"] == (
        "https://flgpusbxipcotgiotdmv.supabase.co/storage/v1/object/nobs-ai/video123/final.mp4"
    )
    assert calls[0]["headers"]["Authorization"] == "Bearer service-role-key"
    assert calls[0]["headers"]["Content-Type"] == "video/mp4"
    assert calls[0]["content"] == b"fake video bytes"


def test_to_url_passes_through_an_already_absolute_url():
    from app.storage import to_url

    url = "https://flgpusbxipcotgiotdmv.supabase.co/storage/v1/object/public/nobs-ai/x/final.mp4"
    assert to_url(url) == url
