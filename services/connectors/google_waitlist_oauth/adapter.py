"""Public "Continue with Google / Continue with YouTube" sign-in for the
waitlist page (apps/web/src/landing) — NOT the same thing as the Gmail or YouTube
connectors in services/connectors/gmail and services/connectors/youtube.
Those are pre-authorized once, by Nobert, for his own account (a refresh
token pasted into Render by hand). This one runs a real, live OAuth
consent screen for a stranger clicking a public button on the waitlist
page, so it needs its own Client ID/Secret (GOOGLE_WAITLIST_CLIENT_ID/
SECRET) registered for a public redirect URI — see
GOOGLE_WAITLIST_OAUTH_SETUP.md for the one-time Google Cloud Console setup,
including the real limitation on the "youtube" variant: Google treats
youtube.readonly as a sensitive scope and requires app verification before
it'll work for anyone outside a short test-user allowlist.

Flow: start() builds the consent-screen URL -> Google redirects back to our
/waitlist/oauth/{provider}/callback with a code -> exchange_code() trades
it for an access token -> fetch_identity() reads the verified email/name
(and, for "youtube", the channel title) -> the router upserts a
WaitlistSignup row. No refresh token is kept — this is a one-shot identity
check for lead capture, not an ongoing connection to anyone's account.
"""

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlencode

import httpx

from services.common.errors import EngineNotConfiguredError

_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
_REQUEST_TIMEOUT_SECONDS = 15

Provider = Literal["google", "youtube"]

_SCOPES: dict[Provider, str] = {
    "google": "openid email profile",
    # readonly is the least-privileged scope that still lets us show the
    # channel name back to Nobert as a qualifying signal — never
    # youtube.upload/manage, this never touches anyone's channel.
    "youtube": "openid email profile https://www.googleapis.com/auth/youtube.readonly",
}


@dataclass
class WaitlistIdentity:
    email: str
    name: str
    google_sub: str
    youtube_channel_title: str | None = None


class GoogleWaitlistOAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def _require_configured(self) -> None:
        if not (self._client_id and self._client_secret):
            raise EngineNotConfiguredError(
                "No GOOGLE_WAITLIST_CLIENT_ID/GOOGLE_WAITLIST_CLIENT_SECRET configured — "
                "see GOOGLE_WAITLIST_OAUTH_SETUP.md for the one-time Google Cloud Console "
                "setup needed before the waitlist's Google/YouTube sign-in buttons work."
            )

    def build_authorize_url(self, provider: Provider, state: str) -> str:
        self._require_configured()
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": _SCOPES[provider],
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{_AUTHORIZE_URL}?{urlencode(params)}"

    def fetch_identity(self, provider: Provider, code: str) -> WaitlistIdentity:
        self._require_configured()
        token_response = httpx.post(
            _TOKEN_URL,
            data={
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": self._redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]

        userinfo_response = httpx.get(
            _USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

        youtube_channel_title = None
        if provider == "youtube":
            channel_response = httpx.get(
                _CHANNELS_URL,
                params={"part": "snippet", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            if channel_response.status_code == 200:
                items = channel_response.json().get("items") or []
                if items:
                    youtube_channel_title = items[0]["snippet"]["title"]
            # A non-200 here (e.g. the sensitive-scope verification above
            # isn't done yet, so Google rejects the scope) isn't fatal —
            # we still got a verified email from userinfo, so the signup
            # still succeeds, just without a channel name attached.

        return WaitlistIdentity(
            email=userinfo["email"],
            name=userinfo.get("name", ""),
            google_sub=userinfo["sub"],
            youtube_channel_title=youtube_channel_title,
        )
