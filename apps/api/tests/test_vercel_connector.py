import pytest

from services.common.errors import EngineNotConfiguredError
from services.connectors.vercel.adapter import VercelConnector


def test_raises_when_not_configured():
    connector = VercelConnector(token="", project_id="")
    with pytest.raises(EngineNotConfiguredError):
        connector.list_deployments()


def test_list_deployments_scopes_to_configured_project(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"deployments": [{"uid": "dpl_1"}]}

    calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append({"url": url, "params": params})
        return _FakeResponse()

    import services.connectors.vercel.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "get", fake_get)

    connector = VercelConnector(token="tok", project_id="prj_123", team_id="team_1")
    deployments = connector.list_deployments(limit=5)

    assert deployments == [{"uid": "dpl_1"}]
    assert calls[0]["url"] == "https://api.vercel.com/v7/deployments"
    assert calls[0]["params"] == {"projectId": "prj_123", "limit": 5, "teamId": "team_1"}


def test_list_env_vars_never_returns_values(monkeypatch):
    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "envs": [
                    {
                        "id": "env_1",
                        "key": "SECRET_KEY",
                        "value": "should-not-appear",
                        "target": ["production"],
                    }
                ]
            }

    import services.connectors.vercel.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "get", lambda *a, **k: _FakeResponse())

    connector = VercelConnector(token="tok", project_id="prj_123")
    envs = connector.list_env_vars()

    assert envs == [{"id": "env_1", "key": "SECRET_KEY", "target": ["production"]}]
    assert "value" not in envs[0]


def test_set_env_var_defaults_target_to_production(monkeypatch):
    posts = []

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"created": {"id": "env_new"}}

    def fake_post(url, headers=None, params=None, json=None, timeout=None):
        posts.append({"url": url, "json": json})
        return _FakeResponse()

    import services.connectors.vercel.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    connector = VercelConnector(token="tok", project_id="prj_123")
    connector.set_env_var("FEATURE_FLAG", "true")

    assert posts[0]["url"] == "https://api.vercel.com/v10/projects/prj_123/env"
    assert posts[0]["json"]["target"] == ["production"]
    assert posts[0]["json"]["key"] == "FEATURE_FLAG"
