"""The NOBS AI connector's MCP server — a small, stateless JSON-RPC 2.0
handler for MCP's "Streamable HTTP" transport (each POST is answered with a
single JSON response; no sessions, no streaming).

Written by hand rather than with the MCP SDK so production gains no new
dependency for ~150 lines of protocol, and so every tool is plain, testable
Python in this file.

WHAT A CONNECTOR KEY CAN DO: import or complete videos, read projects/videos,
and — only because Nobert explicitly asked for it — schedule or publish a
finished video when he tells Claude to (nobs_schedule_publish /
nobs_publish_video; the latter needs confirm=true, and the tool descriptions
and server instructions tell Claude never to do it unprompted). There is
deliberately NO delete, spend, or settings tool. Uploads are always private;
only an explicit publish/schedule makes anything public (CLAUDE.md Part 1).
"""

import json
import logging
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app import publishing
from app.config import settings
from app.connector import importer, jobs
from app.connector.importer import ConnectorImportError, ImportRequest, SceneInput
from app.models.enums import PipelineStage
from app.models.project import Project
from app.models.user import User
from app.models.video import Video
from app.storage import to_url
from services.storage.factory import get_storage_backend

logger = logging.getLogger(__name__)

SERVER_NAME = "nobs-ai"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOLS = ["2025-06-18", "2025-03-26", "2024-11-05"]

_INSTRUCTIONS = (
    "NOBS AI is Nobert's YouTube production studio. Two ways to use it:\n"
    "1) Hand over a video you made yourself: nobs_import_video (direct https link to an MP4, "
    f"max {settings.connector_max_import_mb} MB). It appears as a completed project.\n"
    "2) Produce a video Nobert approved in NOBS AI: nobs_list_claude_jobs, then "
    "nobs_get_claude_job for the script, scenes, voice and style, make the voiceover and "
    "footage, then nobs_complete_claude_job with the finished MP4.\n"
    "If a file only exists in your sandbox, call nobs_upload_instructions.\n"
    "PUBLISHING: you may call nobs_schedule_publish or nobs_publish_video ONLY when Nobert has "
    "explicitly told you, in this conversation, to publish or schedule that specific video "
    "(and for scheduling, the exact date, time and time zone). Never publish or schedule on "
    "your own initiative, never guess a time zone, and always tell him exactly what you did. "
    "Otherwise a finished video waits for him in NOBS AI."
)


@dataclass
class RpcContext:
    db: Session
    user: User
    # The secret path segment, only used to build the direct-upload hint.
    key: str


def _text(payload: Any, *, is_error: bool = False) -> dict:
    body = payload if isinstance(payload, str) else json.dumps(payload, indent=2, default=str)
    return {"content": [{"type": "text", "text": body}], "isError": is_error}


def _dashboard_url(video: Video) -> str:
    return f"{settings.landing_base_url.rstrip('/')}/videos/{video.id}"


def _video_summary(video: Video) -> dict:
    return {
        "video_id": str(video.id),
        "title": video.topic,
        "stage": video.stage.value,
        "duration_seconds": video.target_duration_seconds,
        "video_url": to_url(video.final_video_path),
        "produced_by": video.producer,
        "uploaded_to_youtube": bool(video.youtube_video_id),
        "published": video.youtube_published,
        "scheduled_publish_at": (
            video.scheduled_publish_at.isoformat() if video.scheduled_publish_at else None
        ),
        "publish_error": video.publish_error,
        "open_in_nobs_ai": _dashboard_url(video),
    }


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------


def _storage():
    return get_storage_backend(
        settings.storage_backend,
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.supabase_storage_bucket,
    )


_OPTIONAL_FILES = (
    ("voiceover_path", "voiceover_url", importer._AUDIO, "voiceover"),
    ("captions_path", "captions_url", importer._CAPTIONS, "captions"),
    ("thumbnail_path", "thumbnail_url", importer._IMAGE, "thumbnail"),
)


def _tool_import_video(ctx: RpcContext, args: dict) -> dict:
    title = str(args.get("title") or "").strip()
    video_url = str(args.get("video_url") or "").strip()
    if not title or not video_url:
        return _text("Both 'title' and 'video_url' are required.", is_error=True)

    scenes: list[SceneInput] = []
    for raw in args.get("scenes") or []:
        narration = str((raw or {}).get("narration") or "").strip()
        if not narration:
            return _text("Every scene needs non-empty 'narration'.", is_error=True)
        try:
            seconds = int((raw or {}).get("duration_seconds") or 0)
        except (TypeError, ValueError):
            return _text("Scene 'duration_seconds' must be a whole number.", is_error=True)
        scenes.append(
            SceneInput(
                narration=narration,
                visual_prompt=str((raw or {}).get("visual_prompt") or ""),
                duration_seconds=max(0, seconds),
            )
        )

    max_bytes = settings.connector_max_import_mb * 1024 * 1024
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        video_path = work / "video.mp4"
        importer.download_to_file(video_url, video_path, max_bytes)

        request = ImportRequest(
            title=title,
            project_name=str(args.get("project_name") or importer.DEFAULT_PROJECT_NAME),
            description=str(args.get("description") or ""),
            hook=str(args.get("hook") or ""),
            scenes=scenes,
            video_path=video_path,
        )
        for field_name, url_key, kind, stem in _OPTIONAL_FILES:
            url = str(args.get(url_key) or "").strip()
            if url:
                setattr(request, field_name, importer.fetch_optional(url, kind, work, stem))

        video = importer.import_finished_video(ctx.db, ctx.user, request, _storage(), work)

    summary = _video_summary(video)
    summary["next_step"] = (
        "Imported as a completed project. Nobert reviews it in NOBS AI, then publishes or "
        "schedules it himself. Do not tell him it is live."
    )
    return _text(summary)


def _tool_upload_instructions(ctx: RpcContext, args: dict) -> dict:
    base = settings.api_base_url.rstrip("/")
    return _text(
        {
            "when_to_use": "Only if the finished MP4 exists inside your sandbox and has no "
            "public link. Needs your sandbox to be able to reach the NOBS AI API host.",
            "command": (
                f'curl -sS -X POST "{base}/connector/upload/{ctx.key}" '
                '-F "file=@/path/to/video.mp4" -F "title=Your video title"'
            ),
            "optional_form_fields": [
                "video_id (to finish a job from nobs_list_claude_jobs instead of creating a "
                "new video)",
                "project_name", "description", "hook",
                "voiceover (file)", "captions (file)", "thumbnail (file)",
            ],
            "limit": f"MP4 only, max {settings.connector_max_import_mb} MB.",
            "note": "Treat this command as secret — the URL contains the connector key.",
        }
    )


def _tool_list_projects(ctx: RpcContext, args: dict) -> dict:
    rows = (
        ctx.db.query(Project)
        .filter(Project.owner_id == ctx.user.id)
        .order_by(Project.created_at.desc())
        .limit(50)
        .all()
    )
    return _text([{"project_id": str(p.id), "name": p.name} for p in rows])


def _owned_videos(ctx: RpcContext):
    return (
        ctx.db.query(Video)
        .join(Project, Project.id == Video.project_id)
        .filter(Project.owner_id == ctx.user.id)
    )


def _tool_list_videos(ctx: RpcContext, args: dict) -> dict:
    try:
        limit = min(max(int(args.get("limit") or 10), 1), 50)
    except (TypeError, ValueError):
        limit = 10
    rows = _owned_videos(ctx).order_by(Video.created_at.desc()).limit(limit).all()
    return _text([_video_summary(v) for v in rows])


def _tool_get_video(ctx: RpcContext, args: dict) -> dict:
    try:
        video_id = uuid.UUID(str(args.get("video_id") or ""))
    except ValueError:
        return _text("'video_id' must be a video id from nobs_list_videos.", is_error=True)
    video = _owned_videos(ctx).filter(Video.id == video_id).one_or_none()
    if video is None:
        return _text("Video not found.", is_error=True)
    summary = _video_summary(video)
    summary["stage_detail"] = video.stage_detail
    return _text(summary)


def _owned_video_or_error(ctx: RpcContext, args: dict) -> tuple[Video | None, dict | None]:
    try:
        video_id = uuid.UUID(str(args.get("video_id") or ""))
    except ValueError:
        return None, _text("'video_id' must be a video id from nobs_list_videos.", is_error=True)
    video = _owned_videos(ctx).filter(Video.id == video_id).one_or_none()
    if video is None:
        return None, _text("Video not found.", is_error=True)
    return video, None


def _claude_jobs(ctx: RpcContext):
    return _owned_videos(ctx).filter(
        Video.producer == "claude", Video.stage == PipelineStage.AWAITING_CLAUDE
    )


def _tool_list_claude_jobs(ctx: RpcContext, args: dict) -> dict:
    rows = _claude_jobs(ctx).order_by(Video.created_at).limit(50).all()
    return _text(
        [
            {
                "video_id": str(v.id),
                "topic": v.topic,
                "target_duration_seconds": v.target_duration_seconds,
                "approved": v.storyboard_approved,
            }
            for v in rows
        ]
    )


def _tool_get_claude_job(ctx: RpcContext, args: dict) -> dict:
    video, error = _owned_video_or_error(ctx, args)
    if error:
        return error
    if video.producer != "claude" or video.stage != PipelineStage.AWAITING_CLAUDE:
        return _text("That video isn't waiting for Claude.", is_error=True)
    return _text(jobs.build_brief(ctx.db, video))


def _tool_complete_claude_job(ctx: RpcContext, args: dict) -> dict:
    video, error = _owned_video_or_error(ctx, args)
    if error:
        return error
    video_url = str(args.get("video_url") or "").strip()
    if not video_url:
        return _text("'video_url' is required.", is_error=True)
    if video.producer != "claude" or video.stage != PipelineStage.AWAITING_CLAUDE:
        return _text("That video isn't waiting for Claude.", is_error=True)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        video_path = work / "video.mp4"
        importer.download_to_file(
            video_url, video_path, settings.connector_max_import_mb * 1024 * 1024
        )
        request = ImportRequest(title=video.topic, video_path=video_path)
        for field_name, url_key, kind, stem in _OPTIONAL_FILES:
            url = str(args.get(url_key) or "").strip()
            if url:
                setattr(request, field_name, importer.fetch_optional(url, kind, work, stem))
        done = importer.complete_claude_job(ctx.db, video, request, _storage(), work)

    summary = _video_summary(done)
    summary["next_step"] = (
        "Delivered. The video is complete in NOBS AI; Nobert reviews it and publishes or "
        "schedules it. Do not tell him it is live."
    )
    return _text(summary)


def _tool_schedule_publish(ctx: RpcContext, args: dict) -> dict:
    video, error = _owned_video_or_error(ctx, args)
    if error:
        return error
    raw = str(args.get("publish_at") or "").strip()
    try:
        publish_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return _text(
            "'publish_at' must be an ISO 8601 date-time WITH a time zone, "
            "e.g. 2026-12-01T17:00:00+01:00.",
            is_error=True,
        )
    try:
        publishing.schedule_publish(
            ctx.db, video, publish_at, args.get("title"), args.get("description")
        )
    except publishing.PublishingError as exc:
        # Raised before anything is written, so there is nothing to roll back.
        return _text(str(exc), is_error=True)
    summary = _video_summary(video)
    summary["next_step"] = (
        "Scheduled. It uploads privately and goes public at that time, if the NOBS AI "
        "worker is running. Tell Nobert the exact date, time and time zone you set."
    )
    return _text(summary)


def _tool_cancel_scheduled_publish(ctx: RpcContext, args: dict) -> dict:
    video, error = _owned_video_or_error(ctx, args)
    if error:
        return error
    publishing.cancel_scheduled_publish(ctx.db, video)
    return _text(_video_summary(video))


def _tool_publish_video(ctx: RpcContext, args: dict) -> dict:
    video, error = _owned_video_or_error(ctx, args)
    if error:
        return error
    if args.get("confirm") is not True:
        return _text(
            "Not published. Set confirm=true ONLY if Nobert explicitly told you, in this "
            "conversation, to publish this specific video now.",
            is_error=True,
        )
    try:
        publishing.publish_now(ctx.db, video, args.get("title"), args.get("description"))
    except publishing.PublishingError as exc:
        # Raised before anything is written, so there is nothing to roll back.
        return _text(str(exc), is_error=True)
    summary = _video_summary(video)
    summary["next_step"] = "Published — the video is now public. Tell Nobert."
    return _text(summary)


_STR = {"type": "string"}

TOOLS: dict[str, dict] = {
    "nobs_import_video": {
        "description": (
            "Hand a finished video to NOBS AI. It appears as a completed project (script, "
            "voiceover, captions and thumbnails filed, all pipeline steps ticked) waiting for "
            "Nobert to publish or schedule it. Does NOT publish anything."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["title", "video_url"],
            "properties": {
                "title": {**_STR, "description": "Video title."},
                "video_url": {
                    **_STR,
                    "description": "Direct public https link to the finished MP4.",
                },
                "project_name": {
                    **_STR,
                    "description": "Project to file it under (created if new). "
                    f"Default: {importer.DEFAULT_PROJECT_NAME}.",
                },
                "description": {**_STR, "description": "Short description / summary."},
                "hook": {**_STR, "description": "The opening hook line."},
                "scenes": {
                    "type": "array",
                    "description": "The script as scenes, if you have it.",
                    "items": {
                        "type": "object",
                        "required": ["narration"],
                        "properties": {
                            "narration": _STR,
                            "visual_prompt": _STR,
                            "duration_seconds": {"type": "integer"},
                        },
                    },
                },
                "voiceover_url": {**_STR, "description": "Optional https link to the voiceover."},
                "captions_url": {**_STR, "description": "Optional https link to an .srt/.vtt."},
                "thumbnail_url": {
                    **_STR,
                    "description": "Optional https link to a thumbnail image. If omitted, "
                    "three thumbnail options are taken from the video.",
                },
            },
        },
        "handler": _tool_import_video,
    },
    "nobs_list_claude_jobs": {
        "description": "Videos Nobert approved in NOBS AI and asked YOU (Claude) to produce — "
        "the script and storyboard are approved and waiting for the voiceover and footage.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_list_claude_jobs,
    },
    "nobs_get_claude_job": {
        "description": "The full brief for one approved video: script as scenes (narration + "
        "visual prompt + duration), chosen voice and style, and a suggested YouTube "
        "title/description.",
        "inputSchema": {
            "type": "object",
            "required": ["video_id"],
            "properties": {"video_id": _STR},
        },
        "handler": _tool_get_claude_job,
    },
    "nobs_complete_claude_job": {
        "description": "Hand back the finished video for a job from nobs_list_claude_jobs. "
        "Marks every pipeline step done. Does NOT publish.",
        "inputSchema": {
            "type": "object",
            "required": ["video_id", "video_url"],
            "properties": {
                "video_id": _STR,
                "video_url": {**_STR, "description": "Direct public https link to the MP4."},
                "voiceover_url": _STR,
                "captions_url": _STR,
                "thumbnail_url": _STR,
            },
        },
        "handler": _tool_complete_claude_job,
    },
    "nobs_schedule_publish": {
        "description": "Schedule a finished video to go public at a date and time. ONLY when "
        "Nobert explicitly told you to, with the exact date, time and time zone. It uploads "
        "privately and publishes then.",
        "inputSchema": {
            "type": "object",
            "required": ["video_id", "publish_at"],
            "properties": {
                "video_id": _STR,
                "publish_at": {
                    **_STR,
                    "description": "ISO 8601 WITH time zone, e.g. 2026-12-01T17:00:00+01:00.",
                },
                "title": _STR,
                "description": _STR,
            },
        },
        "handler": _tool_schedule_publish,
    },
    "nobs_cancel_scheduled_publish": {
        "description": "Cancel a video's scheduled publish. The video stays unpublished.",
        "inputSchema": {
            "type": "object",
            "required": ["video_id"],
            "properties": {"video_id": _STR},
        },
        "handler": _tool_cancel_scheduled_publish,
    },
    "nobs_publish_video": {
        "description": "Make a finished video public on YouTube NOW. ONLY when Nobert explicitly "
        "told you, in this conversation, to publish that specific video. Requires confirm=true.",
        "inputSchema": {
            "type": "object",
            "required": ["video_id", "confirm"],
            "properties": {
                "video_id": _STR,
                "confirm": {"type": "boolean"},
                "title": _STR,
                "description": _STR,
            },
        },
        "handler": _tool_publish_video,
    },
    "nobs_upload_instructions": {
        "description": "How to send a finished MP4 that only exists in your sandbox "
        "(no public link) straight to NOBS AI.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_upload_instructions,
    },
    "nobs_list_projects": {
        "description": "List the projects in NOBS AI.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_list_projects,
    },
    "nobs_list_videos": {
        "description": "List recent videos with their stage and whether they are published.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "1-50, default 10."}},
        },
        "handler": _tool_list_videos,
    },
    "nobs_get_video": {
        "description": "Get one video's current status.",
        "inputSchema": {
            "type": "object",
            "required": ["video_id"],
            "properties": {"video_id": _STR},
        },
        "handler": _tool_get_video,
    },
}


# --------------------------------------------------------------------------
# JSON-RPC dispatch
# --------------------------------------------------------------------------


def _error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _call_tool(ctx: RpcContext, params: dict) -> dict:
    tool = TOOLS.get(str(params.get("name")))
    if tool is None:
        return _text(f"Unknown tool '{params.get('name')}'.", is_error=True)
    try:
        return tool["handler"](ctx, params.get("arguments") or {})
    except ConnectorImportError as exc:
        ctx.db.rollback()
        return _text(str(exc), is_error=True)
    except Exception:  # noqa: BLE001 - a tool bug must not become an HTTP 500
        logger.exception("Connector tool %s failed", params.get("name"))
        ctx.db.rollback()
        return _text("Something went wrong inside NOBS AI. Nothing was imported.", is_error=True)


def handle_message(ctx: RpcContext, message: Any) -> dict | None:
    """One JSON-RPC message in, one response out (None for notifications)."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(None, -32600, "Invalid request")
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}

    if "id" not in message:  # notification: never answered
        return None

    if method == "initialize":
        requested = params.get("protocolVersion")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": requested if requested in SUPPORTED_PROTOCOLS
                else SUPPORTED_PROTOCOLS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": _INSTRUCTIONS,
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        tools = [
            {"name": name, "description": t["description"], "inputSchema": t["inputSchema"]}
            for name, t in TOOLS.items()
        ]
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}
    if method == "tools/call":
        return {"jsonrpc": "2.0", "id": msg_id, "result": _call_tool(ctx, params)}
    return _error(msg_id, -32601, f"Method not found: {method}")
