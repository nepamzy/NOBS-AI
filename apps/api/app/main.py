from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.bootstrap import ensure_admin_exists
from app.config import settings
from app.db import SessionLocal
from app.routers import admin, auth, health, payments, projects, spend, styles, videos, voices
from app.routers import settings as settings_router


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    db = SessionLocal()
    try:
        ensure_admin_exists(db)
    finally:
        db.close()
    yield


app = FastAPI(title="NOBS AI API", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(payments.router)
app.include_router(projects.router)
app.include_router(settings_router.router)
app.include_router(spend.router)
app.include_router(styles.router)
app.include_router(videos.router)
app.include_router(voices.router)

# Serves generated voiceovers/clips/captions/thumbnails/final videos so the
# frontend can actually load them (see app/storage.py) — only meaningful for
# STORAGE_BACKEND=local; an S3 backend wouldn't need this mount at all.
Path(settings.local_storage_root).mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.local_storage_root), name="storage")
