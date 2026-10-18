from datetime import UTC, datetime, timedelta

from app.auth.security import hash_lookup_value
from app.models.auth import SignupPin

from services.connectors.youtube.adapter import ChannelIdentity


def _signup_guest(client, db_session, code="654321"):
    pin = SignupPin(
        code_hash=hash_lookup_value(code),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        created_by_user_id=client.admin_user.id,
    )
    db_session.add(pin)
    db_session.flush()
    signup = client.post(
        "/auth/signup",
        json={
            "pin_code": code,
            "email": "guest@example.com",
            "password": "password",
            "display_name": "Guest",
        },
    ).json()
    return signup["token"]


def test_non_admin_cannot_read_connection_status(client, db_session):
    token = _signup_guest(client, db_session)
    response = client.get("/connections/status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_everything_unconfigured_is_reported_honestly(client, monkeypatch):
    from app.config import settings

    for field in (
        "llm_provider",
        "llm_api_key",
        "runpod_api_key",
        "wan_endpoint_id",
        "chatterbox_api_url",
        "github_token",
        "github_default_repo",
        "vercel_api_token",
        "vercel_project_id",
        "google_client_id",
        "google_client_secret",
        "google_refresh_token",
        "google_youtube_client_id",
        "google_youtube_client_secret",
        "google_youtube_refresh_token",
        "clips_youtube_client_id",
        "clips_youtube_client_secret",
        "clips_youtube_refresh_token",
    ):
        monkeypatch.setattr(settings, field, "")

    response = client.get("/connections/status")
    assert response.status_code == 200
    body = response.json()

    assert all(not p["configured"] for p in body["providers"])
    assert all(p["missing"] for p in body["providers"])
    assert all(not ch["configured"] for ch in body["youtube_channels"])
    # Not configured means no live call was ever attempted — never a false negative.
    assert all(ch["connected"] is None for ch in body["youtube_channels"])


def test_llm_configured_reports_the_selected_model_not_the_key(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "sk-super-secret-value")
    monkeypatch.setattr(settings, "llm_model", "claude-sonnet-5")

    response = client.get("/connections/status")
    llm = next(p for p in response.json()["providers"] if p["id"] == "llm")
    assert llm["configured"] is True
    assert "claude-sonnet-5" in llm["detail"]
    assert "sk-super-secret-value" not in response.text


def test_youtube_channel_configured_and_verified_live(client, monkeypatch):
    from app.config import settings
    from app.routers import connections as connections_router

    monkeypatch.setattr(settings, "google_youtube_client_id", "id")
    monkeypatch.setattr(settings, "google_youtube_client_secret", "secret")
    monkeypatch.setattr(settings, "google_youtube_refresh_token", "refresh")

    def fake_identity(self):
        return ChannelIdentity(channel_id="UC123", title="Nobs Main Channel", thumbnail_url=None)

    monkeypatch.setattr(
        connections_router.YouTubeConnector, "get_channel_identity", fake_identity
    )

    response = client.get("/connections/status")
    main = next(
        ch for ch in response.json()["youtube_channels"] if ch["id"] == "youtube_main"
    )
    assert main["configured"] is True
    assert main["connected"] is True
    assert main["channel_title"] == "Nobs Main Channel"
    assert main["error"] is None
    # The clips channel wasn't touched — stays honestly unconfigured.
    clips = next(
        ch for ch in response.json()["youtube_channels"] if ch["id"] == "youtube_clips"
    )
    assert clips["configured"] is False
    assert clips["connected"] is None


def test_youtube_channel_configured_but_token_revoked(client, monkeypatch):
    import httpx
    from app.config import settings
    from app.routers import connections as connections_router

    monkeypatch.setattr(settings, "google_youtube_client_id", "id")
    monkeypatch.setattr(settings, "google_youtube_client_secret", "secret")
    monkeypatch.setattr(settings, "google_youtube_refresh_token", "refresh")

    def fake_identity(self):
        request = httpx.Request("GET", "https://www.googleapis.com/youtube/v3/channels")
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError("revoked", request=request, response=response)

    monkeypatch.setattr(
        connections_router.YouTubeConnector, "get_channel_identity", fake_identity
    )

    response = client.get("/connections/status")
    main = next(
        ch for ch in response.json()["youtube_channels"] if ch["id"] == "youtube_main"
    )
    # Configured, but a live check proves it doesn't actually work — never
    # shown as connected just because the env vars are present.
    assert main["configured"] is True
    assert main["connected"] is False
    assert main["error"]
