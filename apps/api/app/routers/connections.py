"""Read-only, admin-only status for every external integration this app
can use — never whether the env vars' VALUES are right, just whether
they're present, plus (for YouTube only) a real live check. Exists because
nothing else in the API exposes this: every other place this information
shows up is as a side effect of actually trying an action (a 402 from
EngineNotConfiguredError). The Channel Connections, Settings, and Spending
screens need to show configuration state without first attempting
anything — see NOBS AI Frontend Blueprint sections 11/13/10."""

import httpx
from fastapi import APIRouter, Depends

from app.auth.deps import require_admin
from app.config import settings
from app.models.user import User
from app.schemas.connections import ChannelConnectionStatus, ConnectionsStatusRead, ProviderStatus
from services.common.errors import EngineNotConfiguredError
from services.connectors.youtube.adapter import YouTubeConnector
from pydantic import BaseModel

router = APIRouter(prefix="/connections", tags=["connections"])


def _missing(**fields: str) -> list[str]:
    return [name for name, value in fields.items() if not value]


def _llm_status() -> ProviderStatus:
    missing = _missing(LLM_PROVIDER=settings.llm_provider, LLM_API_KEY=settings.llm_api_key)
    return ProviderStatus(
        id="llm",
        name="AI (research, script, assistant)",
        configured=not missing,
        detail=f"Model: {settings.llm_model}" if not missing else "Not configured",
        missing=missing,
    )


def _video_status() -> ProviderStatus:
    if settings.video_provider == "wan_local":
        missing = _missing(LOCAL_WAN_API_URL=settings.local_wan_api_url)
    else:
        missing = _missing(
            RUNPOD_API_KEY=settings.runpod_api_key, WAN_ENDPOINT_ID=settings.wan_endpoint_id
        )
    return ProviderStatus(
        id="video",
        name="Video generation",
        configured=not missing,
        detail=f"Provider: {settings.video_provider}",
        missing=missing,
    )


def _voice_status() -> ProviderStatus:
    if settings.voice_provider == "elevenlabs":
        missing = _missing(ELEVENLABS_API_KEY=settings.elevenlabs_api_key)
    else:
        missing = _missing(CHATTERBOX_API_URL=settings.chatterbox_api_url)
    return ProviderStatus(
        id="voice",
        name="Voice generation",
        configured=not missing,
        detail=f"Provider: {settings.voice_provider}",
        missing=missing,
    )


def _github_status() -> ProviderStatus:
    missing = _missing(
        GITHUB_TOKEN=settings.github_token, GITHUB_DEFAULT_REPO=settings.github_default_repo
    )
    return ProviderStatus(
        id="github",
        name="GitHub (admin assistant)",
        configured=not missing,
        detail=settings.github_default_repo if not missing else "Not configured",
        missing=missing,
    )


def _vercel_status() -> ProviderStatus:
    missing = _missing(
        VERCEL_API_TOKEN=settings.vercel_api_token, VERCEL_PROJECT_ID=settings.vercel_project_id
    )
    return ProviderStatus(
        id="vercel",
        name="Vercel (admin assistant)",
        configured=not missing,
        detail="Configured" if not missing else "Not configured",
        missing=missing,
    )


def _gmail_status() -> ProviderStatus:
    missing = _missing(
        GOOGLE_CLIENT_ID=settings.google_client_id,
        GOOGLE_CLIENT_SECRET=settings.google_client_secret,
        GOOGLE_REFRESH_TOKEN=settings.google_refresh_token,
    )
    return ProviderStatus(
        id="gmail",
        name="Gmail drafts (admin assistant)",
        configured=not missing,
        detail="Configured" if not missing else "Not configured",
        missing=missing,
    )


def _youtube_channel_status(
    channel_id: str, name: str, client_id: str, client_secret: str, refresh_token: str
) -> ChannelConnectionStatus:
    missing = _missing(
        CLIENT_ID=client_id, CLIENT_SECRET=client_secret, REFRESH_TOKEN=refresh_token
    )
    if missing:
        return ChannelConnectionStatus(
            id=channel_id,
            name=name,
            configured=False,
            missing=missing,
            connected=None,
            channel_title=None,
            channel_thumbnail_url=None,
            error=None,
        )

    connector = YouTubeConnector(client_id, client_secret, refresh_token)
    try:
        identity = connector.get_channel_identity()
    except EngineNotConfiguredError as exc:
        # Shouldn't happen since `missing` was already empty, but keep the
        # same honest shape if it ever does.
        return ChannelConnectionStatus(
            id=channel_id,
            name=name,
            configured=True,
            missing=[],
            connected=False,
            channel_title=None,
            channel_thumbnail_url=None,
            error=str(exc),
        )
    except httpx.HTTPStatusError as exc:
        reason = _youtube_failure_reason(exc)
        return ChannelConnectionStatus(
            id=channel_id,
            name=name,
            configured=True,
            missing=[],
            connected=False,
            channel_title=None,
            channel_thumbnail_url=None,
            error=reason,
        )
    except httpx.HTTPError as exc:
        return ChannelConnectionStatus(
            id=channel_id,
            name=name,
            configured=True,
            missing=[],
            connected=False,
            channel_title=None,
            channel_thumbnail_url=None,
            error=f"Couldn't reach YouTube: {exc}",
        )

    return ChannelConnectionStatus(
        id=channel_id,
        name=name,
        configured=True,
        missing=[],
        connected=True,
        channel_title=identity.title,
        channel_thumbnail_url=identity.thumbnail_url,
        error=None,
    )


@router.get("/status", response_model=ConnectionsStatusRead)
def get_connections_status(_admin: User = Depends(require_admin)) -> ConnectionsStatusRead:
    providers = [
        _llm_status(),
        _video_status(),
        _voice_status(),
        _github_status(),
        _vercel_status(),
        _gmail_status(),
    ]
    youtube_channels = [
        _youtube_channel_status(
            "youtube_main",
            "Main channel",
            settings.google_youtube_client_id,
            settings.google_youtube_client_secret,
            settings.google_youtube_refresh_token,
        ),
        _youtube_channel_status(
            "youtube_clips",
            "Secondary channel (Smart Clipping)",
            settings.clips_youtube_client_id,
            settings.clips_youtube_client_secret,
            settings.clips_youtube_refresh_token,
        ),
    ]
    return ConnectionsStatusRead(providers=providers, youtube_channels=youtube_channels)


def _youtube_failure_reason(exc: httpx.HTTPStatusError) -> str:
    """Say which step of the YouTube check failed, so the fix is obvious.

    - The token-refresh call (oauth2.googleapis.com) failing means Google
      rejected the refresh token itself: revoked, expired (apps left in
      Google's "Testing" publishing status expire refresh tokens after about
      7 days), or issued for a different OAuth client than the ID/secret set.
    - A 403 on the YouTube API means the token works but lacks a scope.
    """
    if "oauth2.googleapis.com" in str(exc.request.url):
        return (
            "Google rejected the refresh token. It was revoked, it expired (apps still in "
            "Google's 'Testing' status lose refresh tokens after about 7 days), or it was "
            "issued for a different OAuth client than GOOGLE_YOUTUBE_CLIENT_ID/SECRET. "
            "Generate a new refresh token with the same client."
        )
    if exc.response.status_code == 403:
        return (
            "The token works but YouTube denied the request. It is missing a scope: the "
            "identity check needs youtube.readonly in addition to youtube.upload."
        )
    return f"YouTube rejected the request (HTTP {exc.response.status_code})."


class ConnectionTestResult(BaseModel):
    id: str
    ok: bool
    detail: str


@router.post("/test/{provider_id}", response_model=ConnectionTestResult)
def test_connection(provider_id: str, _admin: User = Depends(require_admin)) -> ConnectionTestResult:
    """Run ONE free check against a single provider, only when an admin asks.

    Never called on page load. Each check uses a read-only endpoint that costs
    nothing (model list, account info, endpoint health, YouTube channels.list),
    so this never spends money or starts a GPU.
    """
    if provider_id == "llm":
        return _test_llm()
    if provider_id == "voice":
        return _test_voice()
    if provider_id == "video":
        return _test_video()
    if provider_id in ("youtube_main", "youtube_clips"):
        return _test_youtube(provider_id)
    return ConnectionTestResult(
        id=provider_id, ok=False, detail="No free test is available for this provider yet."
    )


def _test_llm() -> ConnectionTestResult:
    if not (settings.llm_provider and settings.llm_api_key):
        return ConnectionTestResult(id="llm", ok=False, detail="Not configured.")
    try:
        response = httpx.get(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": settings.llm_api_key, "anthropic-version": "2023-06-01"},
            timeout=15,
        )
    except httpx.HTTPError as exc:
        return ConnectionTestResult(id="llm", ok=False, detail=f"Couldn't reach Anthropic: {exc}")
    if response.status_code == 200:
        return ConnectionTestResult(id="llm", ok=True, detail="Anthropic accepted the key.")
    return ConnectionTestResult(
        id="llm", ok=False, detail=f"Anthropic rejected the key (HTTP {response.status_code})."
    )


def _test_voice() -> ConnectionTestResult:
    if settings.voice_provider != "elevenlabs":
        return ConnectionTestResult(
            id="voice", ok=False, detail="Test is only available for ElevenLabs right now."
        )
    if not settings.elevenlabs_api_key:
        return ConnectionTestResult(id="voice", ok=False, detail="Not configured.")
    try:
        response = httpx.get(
            "https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            timeout=15,
        )
    except httpx.HTTPError as exc:
        return ConnectionTestResult(id="voice", ok=False, detail=f"Couldn't reach ElevenLabs: {exc}")
    if response.status_code == 200:
        return ConnectionTestResult(id="voice", ok=True, detail="ElevenLabs accepted the key.")
    return ConnectionTestResult(
        id="voice", ok=False, detail=f"ElevenLabs rejected the key (HTTP {response.status_code})."
    )


def _test_video() -> ConnectionTestResult:
    if settings.video_provider == "wan_local":
        if not settings.local_wan_api_url:
            return ConnectionTestResult(id="video", ok=False, detail="Not configured.")
        try:
            # Any HTTP response means the laptop server is reachable.
            response = httpx.get(settings.local_wan_api_url, timeout=15)
        except httpx.HTTPError as exc:
            return ConnectionTestResult(
                id="video",
                ok=False,
                detail=f"Couldn't reach your laptop GPU server. Is it running and public? ({exc})",
            )
        return ConnectionTestResult(
            id="video", ok=True, detail=f"Laptop GPU server reachable (HTTP {response.status_code})."
        )
    if not (settings.runpod_api_key and settings.wan_endpoint_id):
        return ConnectionTestResult(id="video", ok=False, detail="Not configured.")
    try:
        response = httpx.get(
            f"https://api.runpod.ai/v2/{settings.wan_endpoint_id}/health",
            headers={"Authorization": f"Bearer {settings.runpod_api_key}"},
            timeout=15,
        )
    except httpx.HTTPError as exc:
        return ConnectionTestResult(id="video", ok=False, detail=f"Couldn't reach Runpod: {exc}")
    if response.status_code == 200:
        return ConnectionTestResult(id="video", ok=True, detail="Runpod endpoint responded.")
    return ConnectionTestResult(
        id="video", ok=False, detail=f"Runpod rejected the request (HTTP {response.status_code})."
    )


def _test_youtube(channel_id: str) -> ConnectionTestResult:
    if channel_id == "youtube_main":
        client_id, client_secret, refresh = (
            settings.google_youtube_client_id,
            settings.google_youtube_client_secret,
            settings.google_youtube_refresh_token,
        )
        name = "Main channel"
    else:
        client_id, client_secret, refresh = (
            settings.clips_youtube_client_id,
            settings.clips_youtube_client_secret,
            settings.clips_youtube_refresh_token,
        )
        name = "Clips channel"
    status = _youtube_channel_status(channel_id, name, client_id, client_secret, refresh)
    if status.connected:
        return ConnectionTestResult(
            id=channel_id, ok=True, detail=f"Connected as {status.channel_title}."
        )
    return ConnectionTestResult(
        id=channel_id, ok=False, detail=status.error or "Not configured."
    )
