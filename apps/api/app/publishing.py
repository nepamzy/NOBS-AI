"""Putting a finished video on YouTube, now or at a chosen time. One place so
the app's buttons, the connector's tools and the worker's timer all follow the
same rules.

Hard rules (CLAUDE.md Part 1 — publishing is externally visible):
  * Upload is always PRIVATE (services/connectors/youtube/adapter.py). Making
    it public is only ever `publish_now`, which is only called because a
    person asked for that exact video — directly, or by telling Claude.
  * A schedule needs a time zone-aware future time, so "5pm" can never be
    silently read as the server's 5pm.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.clip import Clip
from app.models.enums import PipelineStage
from app.models.script import Script
from app.models.video import Video
from services.common.errors import EngineNotConfiguredError
from services.connectors.youtube.adapter import YouTubeConnector

logger = logging.getLogger(__name__)

# A schedule must be at least this far ahead, so the minute-by-minute worker
# can't be asked to fire "right now" through the scheduling path (use publish
# now for that), and a typo'd past date is rejected instead of firing at once.
MIN_LEAD = timedelta(minutes=2)


class PublishingError(Exception):
    """Something the caller can fix. `status` is the HTTP status the REST layer
    should use; the connector just shows the message."""

    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


CHANNELS = ("main", "clips")


def _credentials(channel: str) -> tuple[str, str, str]:
    if channel == "clips":
        return (
            settings.clips_youtube_client_id,
            settings.clips_youtube_client_secret,
            settings.clips_youtube_refresh_token,
        )
    return (
        settings.google_youtube_client_id,
        settings.google_youtube_client_secret,
        settings.google_youtube_refresh_token,
    )


def channel_configured(channel: str) -> bool:
    return all(_credentials(channel))


def _youtube_for(channel: str) -> YouTubeConnector:
    return YouTubeConnector(*_credentials(channel))


def _youtube() -> YouTubeConnector:
    return _youtube_for("main")


SHORT_MAX_SECONDS = 180  # YouTube Shorts: vertical/square, up to 3 minutes
FORMATS = ("short", "long")


def check_format_channel(fmt: str, requested: str | None) -> None:
    """The second (clips) channel is vertical-only, so it takes Shorts and never
    long videos. Checked BEFORE a clip is accepted, so a mismatch is a clear
    refusal rather than a stored clip with nowhere to go."""
    if fmt == "long" and (requested or "auto").strip().lower() == "clips":
        raise PublishingError(
            "The clips channel only takes vertical Shorts. A long video goes to the main "
            "channel.",
            status=422,
        )


def resolve_channel(requested: str | None, fmt: str | None = None) -> str:
    """"auto" (the default) means: the main channel if it is connected,
    otherwise the second (clips) channel. An explicit "main" or "clips" is
    honoured, or refused if that channel isn't connected — never silently
    swapped for the other one."""
    requested = (requested or "auto").strip().lower()
    if fmt == "long":
        # Long (horizontal) videos belong to the main channel only.
        check_format_channel("long", requested)
        requested = "main"
    if requested == "auto":
        for channel in CHANNELS:
            if channel_configured(channel):
                return channel
        raise PublishingError(
            "No YouTube channel is connected yet (see YOUTUBE_SETUP.md).", status=402
        )
    if requested not in CHANNELS:
        raise PublishingError("channel must be 'main', 'clips' or 'auto'.", status=422)
    if not channel_configured(requested):
        raise PublishingError(
            f"The {requested} YouTube channel isn't connected yet (see YOUTUBE_SETUP.md).",
            status=402,
        )
    return requested


@contextmanager
def _youtube_errors() -> Iterator[None]:
    """Turns a failed YouTube/Google call into a message a person can act on,
    instead of raw HTTP-library text."""
    try:
        yield
    except EngineNotConfiguredError as exc:
        raise PublishingError(str(exc), status=402) from exc
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        hint = (
            "the YouTube connection was rejected — reconnect it in Channel Connections"
            if code in (400, 401, 403)
            else "try again in a few minutes"
        )
        raise PublishingError(f"Google/YouTube answered HTTP {code}: {hint}.", status=502) from exc
    except httpx.HTTPError as exc:
        raise PublishingError(
            f"Couldn't reach YouTube ({type(exc).__name__}); try again in a few minutes.",
            status=502,
        ) from exc


def require_youtube_configured() -> None:
    if not (
        settings.google_youtube_client_id
        and settings.google_youtube_client_secret
        and settings.google_youtube_refresh_token
    ):
        raise PublishingError(
            "YouTube isn't connected yet (see YOUTUBE_SETUP.md), so nothing can be "
            "published or scheduled.",
            status=402,
        )


def _require_publishable(video: Video) -> None:
    if video.stage != PipelineStage.COMPLETED or not video.final_video_path:
        raise PublishingError("This video isn't finished yet, so it can't be published.")
    if video.youtube_published:
        raise PublishingError("This video is already public on YouTube.")


def default_title_and_description(db: Session, video: Video) -> tuple[str, str]:
    script = db.query(Script).filter(Script.video_id == video.id).one_or_none()
    return (script.title if script else video.topic), (script.hook if script else video.topic)


def schedule_publish(
    db: Session,
    video: Video,
    publish_at: datetime,
    title: str | None = None,
    description: str | None = None,
) -> Video:
    _require_publishable(video)
    require_youtube_configured()
    if publish_at.tzinfo is None:
        raise PublishingError(
            "The publish time must include a time zone (e.g. 2026-12-01T17:00:00+01:00).",
            status=422,
        )
    publish_at = publish_at.astimezone(UTC)
    if publish_at < datetime.now(UTC) + MIN_LEAD:
        raise PublishingError("That time is in the past (or under 2 minutes away).", status=422)

    default_title, default_description = default_title_and_description(db, video)
    video.scheduled_publish_at = publish_at
    video.youtube_title = (title or video.youtube_title or default_title).strip()[:500]
    video.youtube_description = (
        description if description is not None else video.youtube_description
    ) or default_description
    video.publish_error = None
    db.commit()
    db.refresh(video)
    return video


def cancel_scheduled_publish(db: Session, video: Video) -> Video:
    video.scheduled_publish_at = None
    db.commit()
    db.refresh(video)
    return video


def publish_now(
    db: Session,
    video: Video,
    title: str | None = None,
    description: str | None = None,
) -> Video:
    """Uploads privately first if it isn't on YouTube yet, then makes it
    public. Each step is committed on its own, so a failure after the upload
    never loses the upload."""
    _require_publishable(video)
    require_youtube_configured()
    youtube = _youtube()

    with _youtube_errors():
        if not video.youtube_video_id:
            default_title, default_description = default_title_and_description(db, video)
            result = youtube.upload_video(
                video.final_video_path,
                (title or video.youtube_title or default_title).strip(),
                (description if description is not None else video.youtube_description)
                or default_description,
                [],
            )
            video.youtube_video_id = result.video_id
            db.commit()
        youtube.publish_video(video.youtube_video_id)

    video.youtube_published = True
    video.scheduled_publish_at = None
    video.publish_error = None
    db.commit()
    db.refresh(video)
    return video


def upload_clip(db: Session, clip: Clip, channel: str | None, publish: bool) -> Clip:
    """Uploads a clip PRIVATE to a channel, and — only if `publish` — makes it
    public. A clip that is already on YouTube stays on the channel it went to;
    `channel` only matters for the first upload. Each step commits on its own,
    so a failure after the upload never loses the upload."""
    if not clip.clip_path:
        raise PublishingError("Clip hasn't finished rendering yet")
    if clip.youtube_published:
        raise PublishingError("This clip is already public on YouTube.")

    if clip.youtube_video_id:
        chosen = clip.youtube_channel or "clips"
    else:
        chosen = resolve_channel(channel, clip.format)
    youtube = _youtube_for(chosen)

    with _youtube_errors():
        if not clip.youtube_video_id:
            description = clip.reason
            if clip.format == "short" and "#shorts" not in description.lower():
                description = f"{description}\n\n#Shorts".strip()
            result = youtube.upload_video(clip.clip_path, clip.title, description, [])
            clip.youtube_video_id = result.video_id
            clip.youtube_channel = chosen
            db.commit()
        if publish:
            youtube.publish_video(clip.youtube_video_id)
            clip.youtube_published = True
            db.commit()
    db.refresh(clip)
    return clip
