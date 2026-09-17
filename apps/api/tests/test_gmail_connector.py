import base64

import pytest

from services.common.errors import EngineNotConfiguredError
from services.connectors.gmail.adapter import GmailConnector


def test_raises_when_not_configured():
    connector = GmailConnector(client_id="", client_secret="", refresh_token="")
    with pytest.raises(EngineNotConfiguredError):
        connector.create_draft("someone@example.com", "Hi", "Body text")


def test_create_draft_refreshes_token_and_never_sends(monkeypatch):
    calls = []

    class _TokenResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "access-123"}

    class _DraftResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "draft_1"}

    def fake_post(url, headers=None, data=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "data": data, "json": json})
        if url == "https://oauth2.googleapis.com/token":
            return _TokenResponse()
        return _DraftResponse()

    import services.connectors.gmail.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    connector = GmailConnector(
        client_id="client-id", client_secret="client-secret", refresh_token="refresh-token"
    )
    draft_id = connector.create_draft("someone@example.com", "Subject line", "Body text")

    assert draft_id == "draft_1"
    token_call, draft_call = calls
    assert token_call["data"]["refresh_token"] == "refresh-token"
    assert token_call["data"]["grant_type"] == "refresh_token"
    assert draft_call["url"] == "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
    assert draft_call["headers"]["Authorization"] == "Bearer access-123"

    raw = draft_call["json"]["message"]["raw"]
    decoded = base64.urlsafe_b64decode(raw).decode()
    assert "someone@example.com" in decoded
    assert "Subject line" in decoded
    assert "Body text" in decoded
    assert "NOBS AI" in decoded
    assert "nobs-ai.vercel.app/logo-mark.png" in decoded
    assert "multipart/alternative" in decoded
