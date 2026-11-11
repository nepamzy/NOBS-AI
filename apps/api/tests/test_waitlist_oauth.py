from app.auth.oauth_state import sign_oauth_state
from app.config import settings
from app.models.waitlist_signup import WaitlistSignup


def test_start_redirects_to_not_configured_without_client_id(client):
    response = client.get("/waitlist/oauth/google/start", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"].endswith("/waitlist?oauth_error=not_configured")


def test_start_redirects_to_google_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "google_waitlist_client_id", "test-client-id")
    monkeypatch.setattr(settings, "google_waitlist_client_secret", "test-secret")

    response = client.get("/waitlist/oauth/youtube/start", follow_redirects=False)

    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "youtube.readonly" in location
    assert "client_id=test-client-id" in location


def test_callback_with_provider_error_redirects_with_denied(client):
    response = client.get(
        "/waitlist/oauth/google/callback", params={"error": "access_denied"}, follow_redirects=False
    )
    assert response.headers["location"].endswith("/waitlist?oauth_error=denied")


def test_callback_without_state_redirects_with_failed(client):
    response = client.get(
        "/waitlist/oauth/google/callback", params={"code": "abc"}, follow_redirects=False
    )
    assert response.headers["location"].endswith("/waitlist?oauth_error=failed")


def test_callback_with_state_for_wrong_provider_redirects_with_failed(client):
    state = sign_oauth_state("google")
    response = client.get(
        "/waitlist/oauth/youtube/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )
    assert response.headers["location"].endswith("/waitlist?oauth_error=failed")


def test_callback_success_creates_signup(client, monkeypatch, db_session):
    monkeypatch.setattr(settings, "google_waitlist_client_id", "test-client-id")
    monkeypatch.setattr(settings, "google_waitlist_client_secret", "test-secret")

    import app.routers.waitlist_oauth as waitlist_oauth_module

    from services.connectors.google_waitlist_oauth.adapter import WaitlistIdentity

    def fake_fetch_identity(self, provider, code):
        return WaitlistIdentity(
            email="creator@example.com",
            name="Creator",
            google_sub="sub-123",
            youtube_channel_title="Creator's Channel" if provider == "youtube" else None,
        )

    monkeypatch.setattr(
        waitlist_oauth_module.GoogleWaitlistOAuth, "fetch_identity", fake_fetch_identity
    )

    state = sign_oauth_state("youtube")
    response = client.get(
        "/waitlist/oauth/youtube/callback",
        params={"code": "real-code", "state": state},
        follow_redirects=False,
    )

    assert response.headers["location"].endswith("/waitlist?joined=1")
    signup = db_session.query(WaitlistSignup).filter_by(email="creator@example.com").one()
    assert signup.source == "youtube_oauth"
    assert signup.youtube_channel_title == "Creator's Channel"


def test_callback_success_is_idempotent_for_an_existing_email(client, monkeypatch, db_session):
    monkeypatch.setattr(settings, "google_waitlist_client_id", "test-client-id")
    monkeypatch.setattr(settings, "google_waitlist_client_secret", "test-secret")

    existing = WaitlistSignup(email="already@example.com", name="Already", source="form")
    db_session.add(existing)
    db_session.flush()

    import app.routers.waitlist_oauth as waitlist_oauth_module

    from services.connectors.google_waitlist_oauth.adapter import WaitlistIdentity

    def fake_fetch_identity(self, provider, code):
        return WaitlistIdentity(email="already@example.com", name="Already", google_sub="sub-1")

    monkeypatch.setattr(
        waitlist_oauth_module.GoogleWaitlistOAuth, "fetch_identity", fake_fetch_identity
    )

    state = sign_oauth_state("google")
    client.get(
        "/waitlist/oauth/google/callback",
        params={"code": "real-code", "state": state},
        follow_redirects=False,
    )

    rows = db_session.query(WaitlistSignup).filter_by(email="already@example.com").all()
    assert len(rows) == 1
    assert rows[0].source == "form"  # untouched — the original signup path is kept
