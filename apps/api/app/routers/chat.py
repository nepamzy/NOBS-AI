import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.models.enums import UserRole
from app.models.project import Project
from app.models.user import User
from app.schemas.chat import ChatAttachment, ChatMessage, ChatRequest, ChatResponse
from app.schemas.project import ProjectRead
from app.schemas.script import SceneRegenerateRequest, ScriptRead
from app.schemas.video import VideoCreate, VideoRead
from services.ai.assistant.engine import (
    ADMIN_SYSTEM_PROMPT_ADDENDUM,
    NOBS_SYSTEM_PROMPT,
    NOBS_TOOLS,
    WEB_SEARCH_TOOL,
    run_chat_turn,
)
from services.common.errors import EngineNotConfiguredError

router = APIRouter(prefix="/chat", tags=["chat"])

_MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024  # 15MB raw file
_ALLOWED_ATTACHMENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/pdf",
}


def _attachment_content_block(attachment: ChatAttachment) -> dict:
    if attachment.media_type not in _ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported attachment type {attachment.media_type!r} — "
            "images (PNG/JPEG/GIF/WebP) and PDFs only. Video isn't supported yet.",
        )
    try:
        raw_size = len(base64.b64decode(attachment.data, validate=True))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Attachment data isn't valid base64") from exc
    if raw_size > _MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=400, detail="Attachment too large — 15MB max")

    block_type = "image" if attachment.media_type.startswith("image/") else "document"
    return {
        "type": block_type,
        "source": {"type": "base64", "media_type": attachment.media_type, "data": attachment.data},
    }


def _build_tool_executor(db: Session, user: User):
    """Every tool below calls straight into the same router functions the
    regular REST endpoints use — same ownership checks, same token-balance
    gate, same ApprovalRequiredError behavior. Chat has no elevated access."""
    from app.routers.videos import (
        approve_storyboard as _approve_storyboard,
    )
    from app.routers.videos import (
        create_video as _create_video,
    )
    from app.routers.videos import (
        get_video as _get_video,
    )
    from app.routers.videos import (
        get_video_script as _get_video_script,
    )
    from app.routers.videos import (
        list_videos as _list_videos,
    )
    from app.routers.videos import (
        regenerate_scene as _regenerate_scene,
    )

    def execute(name: str, tool_input: dict) -> object:
        if name == "list_projects":
            projects = db.query(Project).filter(Project.owner_id == user.id).all()
            return [ProjectRead.model_validate(p).model_dump(mode="json") for p in projects]

        if name == "list_videos":
            project_id = tool_input.get("project_id")
            videos = _list_videos(
                project_id=uuid.UUID(project_id) if project_id else None, db=db, user=user
            )
            return [VideoRead.model_validate(v).model_dump(mode="json") for v in videos]

        if name == "get_video":
            video = _get_video(uuid.UUID(tool_input["video_id"]), db=db, user=user)
            return VideoRead.model_validate(video).model_dump(mode="json")

        if name == "create_video":
            payload = VideoCreate(
                project_id=uuid.UUID(tool_input["project_id"]),
                topic=tool_input["topic"],
                target_duration_seconds=tool_input["target_duration_seconds"],
                voice_preset=tool_input.get("voice_preset", ""),
                style_preset=tool_input.get("style_preset", ""),
                run_research=tool_input.get("run_research", True),
            )
            video = _create_video(payload, db=db, user=user)
            return VideoRead.model_validate(video).model_dump(mode="json")

        if name == "get_video_script":
            script = _get_video_script(uuid.UUID(tool_input["video_id"]), db=db, user=user)
            return ScriptRead.model_validate(script).model_dump(mode="json")

        if name == "regenerate_scene":
            scene = _regenerate_scene(
                uuid.UUID(tool_input["video_id"]),
                uuid.UUID(tool_input["scene_id"]),
                SceneRegenerateRequest(instructions=tool_input.get("instructions", "")),
                db=db,
                user=user,
            )
            return {"narration": scene.narration, "visual_prompt": scene.visual_prompt}

        if name == "approve_storyboard":
            video = _approve_storyboard(uuid.UUID(tool_input["video_id"]), db=db, user=user)
            return VideoRead.model_validate(video).model_dump(mode="json")

        return {"error": f"Unknown tool {name!r}"}

    return execute


@router.post("/messages", response_model=ChatResponse)
def send_message(
    payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ChatResponse:
    conversation = [{"role": m.role, "content": m.content} for m in payload.history]

    if payload.attachment is not None:
        user_content = [
            _attachment_content_block(payload.attachment),
            {"type": "text", "text": payload.message},
        ]
    else:
        user_content = payload.message
    conversation.append({"role": "user", "content": user_content})

    # Admin-only, per Nobert's explicit instruction: broader research/coding/
    # security help plus real web search. Every other user keeps the narrow
    # video-creation-only assistant (CLAUDE.md Part 2).
    if user.role == UserRole.ADMIN:
        system_prompt = NOBS_SYSTEM_PROMPT + ADMIN_SYSTEM_PROMPT_ADDENDUM
        tools = [*NOBS_TOOLS, WEB_SEARCH_TOOL]
    else:
        system_prompt = NOBS_SYSTEM_PROMPT
        tools = NOBS_TOOLS

    try:
        result = run_chat_turn(
            settings.llm_provider,
            settings.llm_api_key,
            settings.llm_model,
            conversation,
            _build_tool_executor(db, user),
            system_prompt=system_prompt,
            tools=tools,
        )
    except EngineNotConfiguredError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc

    return ChatResponse(
        reply=result.reply,
        history=[ChatMessage(role=m["role"], content=m["content"]) for m in result.messages],
    )
