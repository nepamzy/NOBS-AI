"""The NOBS AI connector for Claude.

  * Admin endpoints (/connector/keys) create / list / revoke connector keys.
    A key is the secret that lets one outside Claude session file finished
    videos into this account.
  * POST /mcp/{key} is the MCP server itself — the URL pasted into Claude as
    a custom connector. (POST /mcp with `Authorization: Bearer <key>` works
    too, for clients that can send headers.)
  * POST /connector/upload/{key} takes an MP4 directly (multipart) for a
    Claude session whose video only exists in its sandbox.

A key can import videos and read status. It can NOT publish, upload to
YouTube, delete, or spend — see app/connector/mcp.py.
"""

import logging
import secrets
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.auth.security import hash_lookup_value
from app.config import settings
from app.connector import importer
from app.connector.importer import ConnectorImportError, ImportRequest
from app.connector.mcp import RpcContext, _video_summary, handle_message
from app.db import get_db
from app.models.connector_key import ConnectorKey
from app.models.user import User
from app.rate_limit import rate_limit
from services.storage.factory import get_storage_backend

logger = logging.getLogger(__name__)

router = APIRouter(tags=["connector"])

KEY_PREFIX = "nobs_ck_"
_LAST_USED_REFRESH = timedelta(minutes=5)


class ConnectorKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ConnectorKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    last_used_at: datetime | None
    revoked: bool
    created_at: datetime


class ConnectorKeyCreated(ConnectorKeyRead):
    # Shown exactly once, at creation — only a hash is stored.
    key: str
    connector_url: str


def connector_url_for(key: str) -> str:
    return f"{settings.api_base_url.rstrip('/')}/mcp/{key}"


@router.post("/connector/keys", response_model=ConnectorKeyCreated, status_code=201)
def create_connector_key(
    payload: ConnectorKeyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ConnectorKeyCreated:
    raw = KEY_PREFIX + secrets.token_urlsafe(32)
    row = ConnectorKey(
        user_id=admin.id,
        name=payload.name.strip(),
        key_hash=hash_lookup_value(raw),
        key_prefix=raw[: len(KEY_PREFIX) + 4],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ConnectorKeyCreated(
        **ConnectorKeyRead.model_validate(row).model_dump(),
        key=raw,
        connector_url=connector_url_for(raw),
    )


@router.get("/connector/keys", response_model=list[ConnectorKeyRead])
def list_connector_keys(
    db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> list[ConnectorKey]:
    return (
        db.query(ConnectorKey)
        .filter(ConnectorKey.user_id == admin.id)
        .order_by(ConnectorKey.created_at.desc())
        .all()
    )


@router.delete("/connector/keys/{key_id}", status_code=204)
def revoke_connector_key(
    key_id: uuid.UUID, db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> Response:
    row = db.get(ConnectorKey, key_id)
    if row is None or row.user_id != admin.id:
        raise HTTPException(status_code=404, detail="Key not found")
    row.revoked = True
    db.commit()
    return Response(status_code=204)


def _user_for_key(db: Session, raw: str) -> User:
    # One generic message for every failure so a probe learns nothing.
    invalid = HTTPException(status_code=401, detail="Invalid connector key")
    if not raw.startswith(KEY_PREFIX):
        raise invalid
    row = (
        db.query(ConnectorKey)
        .filter(ConnectorKey.key_hash == hash_lookup_value(raw), ConnectorKey.revoked.is_(False))
        .one_or_none()
    )
    if row is None:
        raise invalid
    user = db.get(User, row.user_id)
    if user is None or user.is_suspended:
        raise invalid
    now = datetime.now(UTC)
    if row.last_used_at is None or now - row.last_used_at > _LAST_USED_REFRESH:
        row.last_used_at = now
        db.commit()
    return user


def _serve_mcp(db: Session, key: str, body: Any) -> Response:
    user = _user_for_key(db, key)
    ctx = RpcContext(db=db, user=user, key=key)
    if isinstance(body, list):
        replies = [r for r in (handle_message(ctx, m) for m in body) if r is not None]
        if not replies:
            return Response(status_code=202)
        return JSONResponse(replies)
    reply = handle_message(ctx, body)
    if reply is None:
        return Response(status_code=202)
    return JSONResponse(reply)


_mcp_limit = Depends(rate_limit("mcp", 120, 60))


@router.post("/mcp/{key}", dependencies=[_mcp_limit])
def mcp_with_key_in_path(
    key: str, body: Any = Body(...), db: Session = Depends(get_db)
) -> Response:
    return _serve_mcp(db, key, body)


@router.post("/mcp", dependencies=[_mcp_limit])
def mcp_with_bearer_key(
    body: Any = Body(...),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Response:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid connector key")
    return _serve_mcp(db, authorization.removeprefix("Bearer ").strip(), body)


def _save_upload(upload: UploadFile, dest: Path, max_bytes: int) -> None:
    written = 0
    with dest.open("wb") as handle:
        while chunk := upload.file.read(1024 * 1024):
            written += len(chunk)
            if written > max_bytes:
                raise ConnectorImportError(
                    f"File is over the {max_bytes // (1024 * 1024)} MB limit."
                )
            handle.write(chunk)


@router.post(
    "/connector/upload/{key}",
    dependencies=[Depends(rate_limit("connector-upload", 30, 60))],
)
def upload_finished_video(
    key: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    project_name: str = Form(default=importer.DEFAULT_PROJECT_NAME),
    description: str = Form(default=""),
    hook: str = Form(default=""),
    voiceover: UploadFile | None = File(default=None),
    captions: UploadFile | None = File(default=None),
    thumbnail: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> dict:
    user = _user_for_key(db, key)
    storage = get_storage_backend(
        settings.storage_backend,
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.supabase_storage_bucket,
    )
    try:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            video_path = work / "video.mp4"
            _save_upload(file, video_path, settings.connector_max_import_mb * 1024 * 1024)
            request = ImportRequest(
                title=title,
                project_name=project_name,
                description=description,
                hook=hook,
                video_path=video_path,
            )
            for attr, upload, kind, stem in (
                ("voiceover_path", voiceover, importer._AUDIO, "voiceover"),
                ("captions_path", captions, importer._CAPTIONS, "captions"),
                ("thumbnail_path", thumbnail, importer._IMAGE, "thumbnail"),
            ):
                if upload is not None and upload.filename:
                    dest = work / f"{stem}{importer.suffix_for(upload.filename, kind)}"
                    _save_upload(upload, dest, kind[2])
                    setattr(request, attr, dest)
            video = importer.import_finished_video(db, user, request, storage, work)
    except ConnectorImportError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _video_summary(video)
