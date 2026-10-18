import httpx

from app.config import settings
from app.routers import connections


def test_non_admin_cannot_run_connection_tests(client, db_session):
    from tests.test_connections import _signup_guest

    token = _signup_guest(client, db_session)
    response = client.post(
        "/connections/test/llm", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_unconfigured_llm_test_makes_no_network_call(client, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "")
    monkeypatch.setattr(settings, "llm_api_key", "")

    def boom(*args, **kwargs):
        raise AssertionError("must not call the network when not configured")

    monkeypatch.setattr(connections.httpx, "get", boom)
    response = client.post("/connections/test/llm")
    assert response.status_code == 200
    assert response.json() == {"id": "llm", "ok": False, "detail": "Not configured."}


def test_llm_test_reports_working_on_200(client, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")

    def fake_get(url, **kwargs):
        assert url == "https://api.anthropic.com/v1/models"
        return httpx.Response(200, json={"data": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr(connections.httpx, "get", fake_get)
    body = client.post("/connections/test/llm").json()
    assert body["ok"] is True


def test_llm_test_reports_rejected_key(client, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "bad-key")

    def fake_get(url, **kwargs):
        return httpx.Response(401, request=httpx.Request("GET", url))

    monkeypatch.setattr(connections.httpx, "get", fake_get)
    body = client.post("/connections/test/llm").json()
    assert body["ok"] is False
    assert "401" in body["detail"]


def test_youtube_refresh_failure_is_explained(client, monkeypatch):
    monkeypatch.setattr(settings, "google_youtube_client_id", "cid")
    monkeypatch.setattr(settings, "google_youtube_client_secret", "csec")
    monkeypatch.setattr(settings, "google_youtube_refresh_token", "rtok")

    def fake_identity(self):
        req = httpx.Request("POST", "https://oauth2.googleapis.com/token")
        raise httpx.HTTPStatusError(
            "bad", request=req, response=httpx.Response(400, request=req)
        )

    monkeypatch.setattr(connections.YouTubeConnector, "get_channel_identity", fake_identity)
    body = client.post("/connections/test/youtube_main").json()
    assert body["ok"] is False
    assert "refresh token" in body["detail"].lower()
