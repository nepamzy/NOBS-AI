import base64

import pytest

from services.common.errors import EngineNotConfiguredError
from services.connectors.github.adapter import GitHubConnector


def test_raises_when_not_configured():
    connector = GitHubConnector(token="", repo="")
    with pytest.raises(EngineNotConfiguredError):
        connector.read_file("README.md")


def test_read_file_decodes_base64_content(monkeypatch):
    class _FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"content": base64.b64encode(b"hello world").decode()}

    calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append({"url": url, "params": params})
        return _FakeResponse()

    import services.connectors.github.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "get", fake_get)

    connector = GitHubConnector(token="tok", repo="nepamzy/NOBS-AI")
    content = connector.read_file("README.md", ref="main")

    assert content == "hello world"
    assert calls[0]["url"] == "https://api.github.com/repos/nepamzy/NOBS-AI/contents/README.md"
    assert calls[0]["params"] == {"ref": "main"}


def test_write_file_creates_new_file_without_sha(monkeypatch):
    class _NotFoundResponse:
        status_code = 404

    class _PutResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"commit": {"html_url": "https://github.com/nepamzy/NOBS-AI/commit/abc123"}}

    puts = []

    import services.connectors.github.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "get", lambda *a, **k: _NotFoundResponse())

    def fake_put(url, headers=None, json=None, timeout=None):
        puts.append({"url": url, "json": json})
        return _PutResponse()

    monkeypatch.setattr(adapter_module.httpx, "put", fake_put)

    connector = GitHubConnector(token="tok", repo="nepamzy/NOBS-AI")
    url = connector.write_file("new.txt", "hi there", "add file", "feature-branch")

    assert url == "https://github.com/nepamzy/NOBS-AI/commit/abc123"
    assert "sha" not in puts[0]["json"]
    assert puts[0]["json"]["branch"] == "feature-branch"
    assert base64.b64decode(puts[0]["json"]["content"]) == b"hi there"


def test_create_pull_request_returns_url(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"html_url": "https://github.com/nepamzy/NOBS-AI/pull/1"}

    posts = []

    def fake_post(url, headers=None, json=None, timeout=None):
        posts.append({"url": url, "json": json})
        return _FakeResponse()

    import services.connectors.github.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    connector = GitHubConnector(token="tok", repo="nepamzy/NOBS-AI")
    url = connector.create_pull_request("feature-branch", "My change", "Description")

    assert url == "https://github.com/nepamzy/NOBS-AI/pull/1"
    assert posts[0]["json"]["head"] == "feature-branch"
    assert posts[0]["json"]["base"] == "main"
