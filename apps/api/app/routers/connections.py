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
        reason = "Token was rejected — it may be revoked or missing the required scope."
        if exc.response.status_code == 403:
            reason = "Access denied — check the OAuth client's scopes in Google Cloud Console."
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
