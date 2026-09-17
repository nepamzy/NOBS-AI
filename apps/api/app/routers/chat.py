import base64
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.models.assistant_memory import AssistantMemory
from app.models.enums import UserRole
from app.models.project import Project
from app.models.user import User
from app.rate_limit import rate_limit
from app.schemas.chat import (
    ChatAttachment,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    GeneratedFileRead,
)
from app.schemas.project import ProjectRead
from app.schemas.script import SceneRegenerateRequest, ScriptRead
from app.schemas.video import VideoCreate, VideoRead
from app.storage import to_url
from services.ai.assistant.engine import (
    ADMIN_SYSTEM_PROMPT_ADDENDUM,
    CODE_EXECUTION_TOOL,
    CONNECTOR_TOOLS,
    MEMORY_TOOL,
    NOBS_SYSTEM_PROMPT,
    NOBS_TOOLS,
    WEB_SEARCH_TOOL,
    GeneratedFile,
    run_chat_turn,
)
from services.common.errors import EngineNotConfiguredError
from services.connectors.github.adapter import GitHubConnector
from services.connectors.gmail.adapter import GmailConnector
from services.connectors.vercel.adapter import VercelConnector
from services.storage.factory import get_storage_backend

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


def _store_generated_file(generated: GeneratedFile, user_id: uuid.UUID) -> GeneratedFileRead:
    """Files the code_execution tool writes (e.g. a generated PDF) live only
    in Claude's own Files API, which browsers can't fetch directly — save a
    copy through the same StorageBackend videos use (local disk or Supabase
    Storage) so the frontend gets an ordinary downloadable URL."""
    key = f"chat-outputs/{user_id}/{uuid.uuid4()}-{generated.filename}"
    local_path = Path(settings.local_storage_root) / key
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(generated.content)

    backend = get_storage_backend(
        settings.storage_backend,
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.supabase_storage_bucket,
    )
    stored_path = backend.upload(str(local_path), key)
    return GeneratedFileRead(
        filename=generated.filename, media_type=generated.media_type, url=to_url(stored_path)
    )


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

        if name.startswith("github_"):
            github = GitHubConnector(settings.github_token, settings.github_default_repo)
            if name == "github_read_file":
                ref = tool_input.get("ref", "main")
                return {"content": github.read_file(tool_input["path"], ref)}
            if name == "github_create_branch":
                from_branch = tool_input.get("from_branch", "main")
                github.create_branch(tool_input["branch_name"], from_branch)
                return {"created": tool_input["branch_name"]}
            if name == "github_write_file":
                url = github.write_file(
                    tool_input["path"],
                    tool_input["content"],
                    tool_input["message"],
                    tool_input["branch"],
                )
                return {"commit_url": url}
            if name == "github_create_pull_request":
                url = github.create_pull_request(
                    tool_input["branch"],
                    tool_input["title"],
                    tool_input["body"],
                    tool_input.get("base", "main"),
                )
                return {"pull_request_url": url}

        if name.startswith("vercel_"):
            vercel = VercelConnector(
                settings.vercel_api_token, settings.vercel_project_id, settings.vercel_team_id
            )
            if name == "vercel_list_deployments":
                return vercel.list_deployments(tool_input.get("limit", 10))
            if name == "vercel_get_deployment":
                return vercel.get_deployment(tool_input["deployment_id"])
            if name == "vercel_list_env_vars":
                return vercel.list_env_vars()
            if name == "vercel_set_env_var":
                return vercel.set_env_var(
                    tool_input["key"], tool_input["value"], tool_input.get("target")
                )

        if name == "gmail_create_draft":
            gmail = GmailConnector(
                settings.google_client_id,
                settings.google_client_secret,
                settings.google_refresh_token,
            )
            draft_id = gmail.create_draft(
                tool_input["to"], tool_input["subject"], tool_input["body"]
            )
            return {"draft_id": draft_id, "note": "Saved to Drafts — not sent"}

        if name == "remember":
            _append_memory(db, user.id, tool_input["fact"])
            return {"saved": True}

        return {"error": f"Unknown tool {name!r}"}

    return execute


_MAX_MEMORY_CHARS = 8000  # keeps the notes from silently growing unbounded in every prompt


def _get_memory(db: Session, user_id: uuid.UUID) -> str:
    memory = db.query(AssistantMemory).filter(AssistantMemory.user_id == user_id).one_or_none()
    return memory.content if memory else ""


def _append_memory(db: Session, user_id: uuid.UUID, fact: str) -> None:
    memory = db.query(AssistantMemory).filter(AssistantMemory.user_id == user_id).one_or_none()
    if memory is None:
        memory = AssistantMemory(user_id=user_id, content="")
        db.add(memory)
    updated = f"{memory.content}\n- {fact}".strip()
    # Trim from the oldest end (start of the string) so recent facts survive.
    memory.content = updated[-_MAX_MEMORY_CHARS:]
    db.commit()


@router.post(
    "/messages",
    response_model=ChatResponse,
    dependencies=[Depends(rate_limit("chat", max_requests=20, window_seconds=60))],
)
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
        memory = _get_memory(db, user.id)
        if memory:
            system_prompt += f"\n\nWhat you already know about Nobert:\n{memory}"
        tools = [*NOBS_TOOLS, WEB_SEARCH_TOOL, CODE_EXECUTION_TOOL, *CONNECTOR_TOOLS, MEMORY_TOOL]
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
        files=[_store_generated_file(f, user.id) for f in result.generated_files],
    )
