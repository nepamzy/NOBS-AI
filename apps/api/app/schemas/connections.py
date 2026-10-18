from pydantic import BaseModel


class ProviderStatus(BaseModel):
    """Whether a provider's required settings are present — never whether
    they actually still work. Verifying would mean a real (sometimes paid,
    sometimes unverifiable-in-this-environment) call to that provider on
    every page load, which this status endpoint deliberately never does.
    See `ChannelConnectionStatus` for the one case (YouTube) where a free,
    already-approved, read-only call makes a live check honest to offer."""

    id: str
    name: str
    configured: bool
    detail: str
    missing: list[str]


class ChannelConnectionStatus(BaseModel):
    """`configured` reflects env vars alone. `connected` is the result of an
    actual live API call made at request time when configured — None means
    that call wasn't attempted (not configured, so there's nothing to
    check)."""

    id: str
    name: str
    configured: bool
    missing: list[str]
    connected: bool | None
    channel_title: str | None
    channel_thumbnail_url: str | None
    error: str | None


class ConnectionsStatusRead(BaseModel):
    providers: list[ProviderStatus]
    youtube_channels: list[ChannelConnectionStatus]
