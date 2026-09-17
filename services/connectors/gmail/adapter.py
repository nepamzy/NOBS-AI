"""Gmail connector — drafts only, by explicit instruction: it must never
send an email on its own. Every draft still needs Nobert to open Gmail,
review it, and hit send himself — the one truly safe way to let an AI
"write emails for you" without risking one going out wrong or to the
wrong person.

Auth: a Google OAuth refresh token (GOOGLE_REFRESH_TOKEN), exchanged here
for a short-lived access token on every call via Google's token endpoint —
never a permanent access token, and never the user's Gmail password (Gmail
has no API-key auth path; OAuth is the only option). Getting that refresh
token is a one-time setup Nobert has to do himself (Google Cloud Console
project + OAuth consent screen + a local authorization flow) — this
adapter can't obtain one on its own since that requires an interactive
browser consent step tied to his Google account.
"""

import base64
from email.mime.text import MIMEText

import httpx

from services.common.errors import EngineNotConfiguredError

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_DRAFTS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
_REQUEST_TIMEOUT_SECONDS = 30


class GmailConnector:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token

    def _require_configured(self) -> None:
        if not (self._client_id and self._client_secret and self._refresh_token):
            raise EngineNotConfiguredError(
                "No GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET/GOOGLE_REFRESH_TOKEN "
                "configured — the Gmail connector needs a one-time OAuth "
                "setup in Google Cloud Console before it can draft anything."
            )

    def _access_token(self) -> str:
        response = httpx.post(
            _TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def create_draft(self, to: str, subject: str, body: str) -> str:
        """Returns the draft's id — never sent, only visible in Gmail's
        Drafts folder until Nobert sends it himself."""
        self._require_configured()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")

        response = httpx.post(
            _DRAFTS_URL,
            headers={"Authorization": f"Bearer {self._access_token()}"},
            json={"message": {"raw": raw}},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["id"]
